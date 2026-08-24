#!/usr/bin/env python3
import argparse
import ast
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ADJUDICATION = ROOT / "evals" / "adjudication.json"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export sanitized deslop benchmark evidence from agent-skill-eval artifacts."
    )
    parser.add_argument("iteration_dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--adjudication", type=Path, default=DEFAULT_ADJUDICATION)
    parser.add_argument("--repository-slug", default="MrZoyo/deslop-GPT")
    parser.add_argument("--repository-commit")
    parser.add_argument("--corpus", default="dev-v1")
    parser.add_argument("--filename-timezone", default="Asia/Shanghai")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def load_json_lines(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def utc_timestamp(value: str) -> str:
    return value.replace("+00:00", "Z")


def unique_value(values: list[object]) -> object:
    unique = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique[0] if len(unique) == 1 else unique


def mean(values: list[float | int | None]) -> float | None:
    known = [float(value) for value in values if value is not None]
    return sum(known) / len(known) if known else None


def rate(passed: int, total: int) -> float | None:
    return passed / total if total else None


def gate_name(assertion: dict) -> str:
    text = str(assertion.get("text", ""))
    if text == "The run respected its side-effect contract":
        return "side_effect_contract"
    if text.startswith("hidden adjudication for "):
        return "semantic"
    if text.startswith("remaining unittest suite for "):
        return "remaining_tests"
    if text.startswith("negative-change budget for "):
        return "negative_change_budget"
    if text.startswith("Codex skill discovery"):
        return "skill_discovery"
    if text == "The run stayed within its budget":
        return "run_budget"
    return "other"


def parse_negative_budget(evidence: str) -> dict:
    line_match = re.search(r"nonblank_python_line_delta=(-?\d+)", evidence)
    new_files_match = re.search(r"new_files=(\[.*?\]); deleted_files=", evidence)
    deleted_files_match = re.search(r"deleted_files=(\[.*?\]); structural_delta=", evidence)
    structural_match = re.search(r"structural_delta=(\{.*\})$", evidence)
    return {
        "nonblank_python_line_delta": int(line_match.group(1)) if line_match else None,
        "new_files": ast.literal_eval(new_files_match.group(1)) if new_files_match else None,
        "deleted_files": ast.literal_eval(deleted_files_match.group(1)) if deleted_files_match else None,
        "structural_delta": json.loads(structural_match.group(1)) if structural_match else None,
    }


def parse_remaining_tests(evidence: str) -> dict:
    count_match = re.search(r"tests=(\d+)", evidence)
    return {"count": int(count_match.group(1)) if count_match else None}


def trajectory_counts(stdout_path: Path) -> dict[str, int]:
    counts = {
        "completed_turns": 0,
        "completed_commands": 0,
        "completed_file_changes": 0,
        "agent_messages": 0,
    }
    if not stdout_path.is_file():
        return counts
    for line in stdout_path.read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "turn.completed":
            counts["completed_turns"] += 1
        if event.get("type") != "item.completed":
            continue
        item_type = event.get("item", {}).get("type")
        if item_type == "command_execution":
            counts["completed_commands"] += 1
        elif item_type == "file_change":
            counts["completed_file_changes"] += 1
        elif item_type == "agent_message":
            counts["agent_messages"] += 1
    return counts


def build_start_order(progress: list[dict]) -> tuple[dict[tuple, int], list[dict]]:
    sequence_by_identity = {}
    actual_order = []
    for event in progress:
        if event.get("event") != "run_started":
            continue
        identity = (
            str(event["eval_id"]),
            str(event["agent"]),
            bool(event["with_skill"]),
            int(event.get("run_index", 1)),
        )
        sequence = len(actual_order) + 1
        sequence_by_identity[identity] = sequence
        actual_order.append(
            {
                "sequence": sequence,
                "case_id": identity[0],
                "agent": identity[1],
                "with_skill": identity[2],
                "run_index": identity[3],
            }
        )
    return sequence_by_identity, actual_order


def parse_run(
    metadata_path: Path,
    classifications: dict[str, str],
    sequence_by_identity: dict[tuple, int],
) -> dict:
    run_dir = metadata_path.parent
    metadata = load_json(metadata_path)
    timing = load_json(run_dir / "timing.json")
    grading = load_json(run_dir / "grading.json")
    case_id = str(metadata["eval_id"])
    identity = (
        case_id,
        str(metadata["agent"]),
        bool(metadata["with_skill"]),
        int(metadata.get("run_index", 1)),
    )

    gates = {}
    other_assertions = []
    for assertion in grading["assertion_results"]:
        name = gate_name(assertion)
        gate = {
            "passed": bool(assertion.get("passed")),
            "evidence": assertion.get("evidence"),
        }
        if name == "other":
            other_assertions.append({"text": assertion.get("text"), **gate})
        else:
            gates[name] = gate
    if "semantic" not in gates:
        raise ValueError(f"{metadata_path}: missing hidden semantic adjudication")

    if "remaining_tests" in gates:
        gates["remaining_tests"].update(
            parse_remaining_tests(str(gates["remaining_tests"].get("evidence", "")))
        )
    negative = None
    structural_delta = None
    if "negative_change_budget" in gates:
        negative = {
            "passed": gates["negative_change_budget"]["passed"],
            **parse_negative_budget(
                str(gates["negative_change_budget"].get("evidence", ""))
            ),
        }
        structural_delta = negative.pop("structural_delta")

    diagnostics_path = run_dir / "outputs" / "diagnostics.json"
    diagnostics = load_json(diagnostics_path).get("details") if diagnostics_path.is_file() else None
    summary = grading["summary"]
    full_pass = summary.get("failed", 0) == 0 and summary.get("total", 0) > 0
    result = {
        "sequence": sequence_by_identity.get(identity),
        "case_id": case_id,
        "expected": classifications.get(case_id, "audit"),
        "agent": identity[1],
        "with_skill": identity[2],
        "run_index": identity[3],
        "full_pass": full_pass,
        "assertions_passed": summary.get("passed", 0),
        "assertions_total": summary.get("total", 0),
        "assertion_pass_rate": summary.get("pass_rate"),
        "gates": gates,
        "timing": {
            "duration_ms": timing.get("duration_ms"),
            "total_tokens": timing.get("total_tokens"),
            "input_tokens": timing.get("input_tokens"),
            "cached_input_tokens": timing.get("cached_tokens"),
            "non_cached_input_tokens": timing.get("non_cached_input_tokens"),
            "output_tokens": timing.get("output_tokens"),
            "reasoning_output_tokens": timing.get("reasoning_output_tokens"),
            "cost_usd": timing.get("cost_usd"),
            "retries": timing.get("retries"),
            "exit_code": timing.get("exit_code"),
            "timed_out": timing.get("timed_out"),
        },
        "trajectory": trajectory_counts(run_dir / "outputs" / "stdout.log"),
    }
    if metadata.get("skill_discovery") is not None:
        result["skill_discovery"] = metadata["skill_discovery"]
    if diagnostics is not None:
        result["diagnostics"] = diagnostics
    if negative is not None:
        result["negative_change_budget"] = negative
    if structural_delta is not None:
        result["structural_delta"] = structural_delta
    if other_assertions:
        result["other_assertions"] = other_assertions
    return result


def metric(passed_rows: list[dict]) -> dict:
    passed = sum(row["full_pass"] for row in passed_rows)
    return {"passed": passed, "total": len(passed_rows), "rate": rate(passed, len(passed_rows))}


def config_aggregate(rows: list[dict]) -> dict:
    semantic = [row for row in rows if row["expected"] != "audit"]
    preservation = [row for row in rows if row["expected"] == "preserve"]
    simplification = [row for row in rows if row["expected"] == "simplify"]
    audit = [row for row in rows if row["expected"] == "audit"]
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        groups[(row["case_id"], row["agent"])].append(row)
    pass_at_k = rate(
        sum(any(run["full_pass"] for run in group) for group in groups.values()),
        len(groups),
    )
    return {
        "behavior_preservation": metric(preservation),
        "slop_removal_recall": metric(simplification),
        "semantic_full_case_pass": metric(semantic),
        "authorization_safety": metric(audit),
        "all_case_full_pass": metric(rows),
        "pass_at_k": pass_at_k,
        "k": max((row["run_index"] for row in rows), default=0),
        "mean_assertion_pass_rate_secondary": mean(
            [row["assertion_pass_rate"] for row in rows]
        ),
        "mean_wall_time_seconds": mean(
            [row["timing"]["duration_ms"] / 1000 for row in rows]
        ),
        "mean_total_tokens": mean([row["timing"]["total_tokens"] for row in rows]),
        "mean_cached_input_tokens": mean(
            [row["timing"]["cached_input_tokens"] for row in rows]
        ),
        "mean_non_cached_input_tokens": mean(
            [row["timing"]["non_cached_input_tokens"] for row in rows]
        ),
        "mean_output_tokens": mean([row["timing"]["output_tokens"] for row in rows]),
        "mean_reasoning_output_tokens": mean(
            [row["timing"]["reasoning_output_tokens"] for row in rows]
        ),
        "mean_completed_commands": mean(
            [row["trajectory"]["completed_commands"] for row in rows]
        ),
        "mean_agent_messages": mean(
            [row["trajectory"]["agent_messages"] for row in rows]
        ),
    }


def paired_outcomes(runs: list[dict]) -> dict:
    pairs: dict[tuple[str, str, int], dict[bool, dict]] = defaultdict(dict)
    for run in runs:
        pairs[(run["case_id"], run["agent"], run["run_index"])][run["with_skill"]] = run
    outcomes = []
    for (case_id, agent, run_index), configurations in sorted(pairs.items()):
        if set(configurations) != {False, True}:
            continue
        baseline = configurations[False]["full_pass"]
        skill = configurations[True]["full_pass"]
        if baseline and skill:
            outcome = "both_pass"
        elif not baseline and skill:
            outcome = "skill_improves"
        elif baseline and not skill:
            outcome = "skill_regresses"
        else:
            outcome = "both_fail"
        outcomes.append(
            {
                "case_id": case_id,
                "expected": configurations[False]["expected"],
                "agent": agent,
                "run_index": run_index,
                "baseline_pass": baseline,
                "skill_pass": skill,
                "outcome": outcome,
            }
        )

    categories = ("both_pass", "skill_improves", "skill_regresses", "both_fail")
    summaries = {}
    for label, expected in (
        ("all", None),
        ("simplify", "simplify"),
        ("preserve", "preserve"),
        ("audit", "audit"),
    ):
        selected = [row for row in outcomes if expected is None or row["expected"] == expected]
        summaries[label] = {category: sum(row["outcome"] == category for row in selected) for category in categories}
        summaries[label]["total"] = len(selected)
    return {"summary": summaries, "cases": outcomes}


def delta(without: dict, with_skill: dict) -> dict:
    fields = (
        "mean_assertion_pass_rate_secondary",
        "mean_wall_time_seconds",
        "mean_total_tokens",
        "mean_cached_input_tokens",
        "mean_non_cached_input_tokens",
        "mean_output_tokens",
        "mean_reasoning_output_tokens",
        "mean_completed_commands",
        "mean_agent_messages",
    )
    result = {}
    for field in fields:
        left = without.get(field)
        right = with_skill.get(field)
        result[field] = right - left if left is not None and right is not None else None
    for field in (
        "behavior_preservation",
        "slop_removal_recall",
        "semantic_full_case_pass",
        "authorization_safety",
        "all_case_full_pass",
    ):
        left = without[field]["rate"]
        right = with_skill[field]["rate"]
        result[field] = right - left if left is not None and right is not None else None
    return result


def git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def main() -> None:
    arguments = parse_arguments()
    iteration_dir = arguments.iteration_dir.resolve()
    metadata = load_json(iteration_dir / "evals_meta.json")
    progress = load_json_lines(iteration_dir / "progress.jsonl")
    summary = load_json(iteration_dir / "summary.json")
    adjudication = load_json(arguments.adjudication)
    classifications = {case["id"]: case["expected"] for case in adjudication["cases"]}
    sequence_by_identity, actual_order = build_start_order(progress)

    runs = [
        parse_run(path, classifications, sequence_by_identity)
        for path in sorted(iteration_dir.rglob("run_meta.json"))
    ]
    runs.sort(key=lambda run: run["sequence"] or 0)
    if len(runs) != summary["runs_completed"]:
        raise ValueError(
            f"found {len(runs)} complete run directories, summary reports {summary['runs_completed']}"
        )
    if summary.get("errors") or summary.get("skipped_runs"):
        raise ValueError("cannot export a complete result with errored or skipped runs")

    first_event = progress[0]
    last_event = progress[-1]
    repository_metadata = metadata.get("benchmark_repository", {})
    execution = metadata.get("execution", {})
    codex_environment = metadata.get("codex_environment", {})
    run_metadata = [load_json(path) for path in sorted(iteration_dir.rglob("run_meta.json"))]
    without = config_aggregate([run for run in runs if not run["with_skill"]])
    with_skill = config_aggregate([run for run in runs if run["with_skill"]])
    timings = [run["timing"] for run in runs]
    known_costs = [timing["cost_usd"] for timing in timings if timing["cost_usd"] is not None]
    skill_size = metadata["skill_size"]

    result = {
        "schema": "deslop-eval-result-v2",
        "status": "internal-development-diagnostic",
        "public_performance_claim": False,
        "run_window": {
            "started_at_utc": utc_timestamp(first_event["ts"]),
            "completed_at_utc": utc_timestamp(last_event["ts"]),
            "filename_timezone": arguments.filename_timezone,
        },
        "repository": {
            "slug": arguments.repository_slug,
            "commit": arguments.repository_commit
            or repository_metadata.get("commit")
            or git_commit(),
            "dirty_at_run_start": repository_metadata.get("dirty"),
            "corpus": arguments.corpus,
            "corpus_role": adjudication.get("corpus_role"),
            "cases": summary["eval_ids"],
        },
        "configuration": {
            "harness": f"agent-skill-eval=={unique_value([row['harness_version'] for row in run_metadata])}",
            "agent_cli": unique_value([row.get("agent_cli_version") for row in run_metadata]),
            "model": unique_value([row.get("model") for row in run_metadata]),
            "reasoning_effort": unique_value(
                [row.get("reasoning_effort") for row in run_metadata]
            ),
            "runs_per_case_configuration": summary["runs_per_case"],
            "model_calls": len(runs),
            "concurrency": execution.get("concurrency"),
            "max_retries": execution.get("agent_max_retries"),
            "timeout_seconds": execution.get("agent_timeout_seconds"),
            "sandbox": codex_environment.get("sandbox"),
            "network": codex_environment.get("network"),
            "approval_policy": codex_environment.get("approval_policy"),
            "local_config": codex_environment.get("local_config"),
            "baseline": "same-strong-evidence-backed-cleanup-prompt-without-skill",
            "post_grade_hook": "python3 evals/grade_case.py",
        },
        "task_order": {
            **metadata.get("task_order", {"strategy": "upstream-fixed-skill-then-baseline"}),
            "actual_start_order": actual_order,
        },
        "skill": {
            "path": "skill/deslop",
            "content_hash": metadata["skill_hash"],
            "payload_files": skill_size["files"],
            "payload_bytes": skill_size["bytes"],
            "payload_words": skill_size["words"],
        },
        "aggregate": {
            "without_skill": without,
            "with_skill": with_skill,
            "delta_with_minus_without": delta(without, with_skill),
            "paired_outcomes": paired_outcomes(runs),
            "all_calls": {
                "total_tokens": sum(timing["total_tokens"] for timing in timings),
                "input_tokens": sum(timing["input_tokens"] for timing in timings),
                "cached_input_tokens": sum(
                    timing["cached_input_tokens"] for timing in timings
                ),
                "non_cached_input_tokens": sum(
                    timing["non_cached_input_tokens"] for timing in timings
                ),
                "output_tokens": sum(timing["output_tokens"] for timing in timings),
                "reasoning_output_tokens": sum(
                    timing["reasoning_output_tokens"] or 0 for timing in timings
                ),
                "cost_usd": sum(known_costs) if len(known_costs) == len(timings) else None,
                "cost_note": None
                if len(known_costs) == len(timings)
                else "Unavailable; at least one run reported no cost telemetry.",
            },
        },
        "runs": runs,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Exported {len(runs)} sanitized runs to {arguments.output}")


if __name__ == "__main__":
    main()
