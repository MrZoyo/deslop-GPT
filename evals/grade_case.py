#!/usr/bin/env python3
import ast
import hashlib
import importlib
import json
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def source(workspace: Path, name: str) -> str:
    return (workspace / name).read_text()


def function_names(workspace: Path, name: str = "app.py") -> set[str]:
    tree = ast.parse(source(workspace, name))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def load_module(workspace: Path, name: str = "app"):
    sys.path.insert(0, str(workspace))
    try:
        importlib.invalidate_caches()
        return importlib.import_module(name)
    finally:
        sys.path.pop(0)


def c01a(workspace: Path) -> str:
    names = function_names(workspace)
    require("first_record" not in names, "unused first_record helper remains")
    require("json_equal_via_digest" not in names, "unused digest equality helper remains")
    require("hashlib" not in source(workspace, "app.py"), "dead digest dependency remains")
    app = load_module(workspace)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "episode.jsonl"
        path.write_text('{"type":"header","fps":60}\n{"type":"result","passed":true}\n')
        header, result = app.load_episode(path)
    require(header["fps"] == 60 and result["passed"] is True, "episode behavior regressed")
    return "dead parser and digest helpers removed; episode reader still works"


def c01b(workspace: Path) -> str:
    app = load_module(workspace)
    require(callable(app.load_episode), "published load_episode facade was removed")
    consumer = load_module(workspace, "external_consumer")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "episode.jsonl"
        path.write_text('{"type":"header"}\n{"type":"result","passed":true}\n')
        require(consumer.episode_passed(path), "external consumer import path broke")
    return "published facade remains usable by an external consumer"


def c02a(workspace: Path) -> str:
    tests = source(workspace, "test_app.py")
    require("assertTrue(all(" not in tests, "redundant aggregate assertion remains")
    test_names = {
        node.name
        for node in ast.walk(ast.parse(tests))
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    }
    require(
        test_names == {"test_completed_results_have_output_directories"},
        "stronger per-result test was removed or replaced with test proliferation",
    )
    app = load_module(workspace)
    with tempfile.TemporaryDirectory() as directory:
        results = app.completed_results(Path(directory))
        require(len(results) == 2, "result count changed")
        require(all(item.output_path.is_dir() for item in results), "output contract regressed")
    return "aggregate assertion removed; stronger per-result contract remains"


def c02b(workspace: Path) -> str:
    app = load_module(workspace)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)

        def fail() -> bytes:
            raise RuntimeError("injected encoder failure")

        try:
            app.publish_episode(root, fail)
        except RuntimeError:
            pass
        else:
            raise AssertionError("encoder failure was swallowed")
        require(not (root / "episode.bin.partial").exists(), "partial output leaked")
        require(not (root / "episode.bin").exists(), "failed output was published")
    return "failure propagates and exact partial output is removed"


def c03a(workspace: Path) -> str:
    text = source(workspace, "app.py")
    for option in ("--frame-rate", "--workers", "--include-sidecars"):
        require(text.count(option) == 1, f"option definition still duplicated: {option}")
    app = load_module(workspace)
    arguments = ["--frame-rate", "24", "--workers", "2", "--include-sidecars"]
    main = vars(app.build_main_parser().parse_args(arguments))
    standalone = vars(app.build_standalone_parser().parse_args(arguments))
    require(main == standalone, "entrypoint options drifted")
    return "one option owner serves both real parser consumers"


def c03b(workspace: Path) -> str:
    app = load_module(workspace)
    require(callable(app.convert_to_v3), "version bridge entrypoint was removed")
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source_path = root / "source"
        output = root / "output"
        source_path.write_text("raw")
        stages: list[str] = []
        intermediates: list[Path] = []

        def to_v2(_source: Path, intermediate: Path) -> None:
            intermediate.mkdir()
            (intermediate / "data").write_text("v2")
            stages.append("v2")
            intermediates.append(intermediate)

        def to_v3(intermediate: Path, target: Path) -> None:
            target.write_text((intermediate / "data").read_text() + "->v3")
            stages.append("v3")

        app.convert_to_v3(source_path, output, to_v2, to_v3)
        require(stages == ["v2", "v3"], "format stages were not both executed in order")
        require(output.read_text() == "v2->v3", "v3 output changed")
        require(not intermediates[0].exists(), "temporary v2 dataset was not cleaned")
    return "wrapper preserves two format boundaries and temporary lifecycle"


def c04a(workspace: Path) -> str:
    app = load_module(workspace)
    parameters = app.convert_records.__code__.co_varnames[: app.convert_records.__code__.co_argcount]
    require("continue_on_error" not in parameters, "ineffective continue_on_error flag remains")
    require("fail_fast" not in parameters, "contradictory fail_fast flag remains")
    seen: list[str] = []

    def encode(value: str) -> bytes:
        seen.append(value)
        if value == "bad":
            raise ValueError("injected failure")
        return value.encode()

    try:
        app.convert_records(["good", "bad", "after"], encode)
    except ValueError:
        pass
    else:
        raise AssertionError("record failure did not propagate directly")
    require(seen == ["good", "bad"], "conversion continued after a production failure")
    return "contradictory recovery flags removed; production conversion fails directly"


def c04b(workspace: Path) -> str:
    app = load_module(workspace)
    require(app.read_actions({"action": [1]}) == [1.0], "current protocol broke")
    require(app.read_actions({"actions": [2]}) == [2.0], "documented legacy protocol broke")
    try:
        app.read_actions({"action": "bad"})
    except TypeError:
        pass
    else:
        raise AssertionError("invalid current payload was hidden by fallback")
    return "precise KeyError fallback preserves current and supported legacy protocols"


def c05a(workspace: Path) -> str:
    text = source(workspace, "app.py")
    require("ROTATION_CUTOFF" not in text, "timestamp cutoff inference remains")
    require("recorded_at" not in text, "recording time still controls pixel transform")
    app = load_module(workspace)
    require(app.transform_frame((1, 2, 3), rotate=True) == (3, 2, 1), "explicit rotation broke")
    require(app.transform_frame((1, 2, 3), rotate=False) == (1, 2, 3), "explicit identity broke")
    return "implicit timestamp inference removed; explicit orientation remains"


def c05b(workspace: Path) -> str:
    app = load_module(workspace)
    try:
        app.decode_frame(b"x", encoded_format="", decoded_size=(640, 352), rotate=False)
    except ValueError:
        pass
    else:
        raise AssertionError("missing external format was guessed")
    try:
        app.decode_frame(b"x", encoded_format="h264", decoded_size=(640, 480), rotate=False)
    except ValueError:
        pass
    else:
        raise AssertionError("wrong calibrated pixel space was accepted")
    return "external format and calibrated geometry gates remain"


def c06a(workspace: Path) -> str:
    app = load_module(workspace)
    app.validate_camera_adapter(app.ConversionOptions(motion_threshold=1e-4))
    for options in (
        app.ConversionOptions(frame_size=(640, 480)),
        app.ConversionOptions(rgb_processing="recorded"),
    ):
        try:
            app.validate_camera_adapter(options)
        except ValueError:
            continue
        raise AssertionError("real camera adapter contract was removed")
    return "redundant default lock removed; geometry and processing contracts remain"


def c06b(workspace: Path) -> str:
    app = load_module(workspace)
    mixed = [app.VideoMessage(0.0, "h264", 0), app.VideoMessage(30.0, "hevc", 1)]
    try:
        app.select_video_frames(mixed, [0.0], max_fill_gap_ms=10.0)
    except ValueError:
        pass
    else:
        raise AssertionError("mixed external formats were accepted")
    try:
        app.select_video_frames(
            [app.VideoMessage(0.0, "h264", 0)], [50.0], max_fill_gap_ms=10.0
        )
    except ValueError:
        pass
    else:
        raise AssertionError("excessive source-frame gap was accepted")
    return "format consistency and temporal quality gates remain"


def c07a(workspace: Path) -> str:
    text = source(workspace, "app.py")
    require("hashlib" not in text, "adapter still owns duplicate hashing implementation")
    require("SENSITIVE_TOKENS" not in text, "adapter still duplicates sensitive-key policy")
    app = load_module(workspace)
    result = app.sanitize_metadata({"episode": {"config_text": "private", "source": "robot"}})
    require(result["episode"]["config_text"] == "<omitted>", "compatibility contract broke")
    require(result["episode"]["source"] == "robot", "safe metadata was lost")
    return "duplicate sanitizer removed while adapter entrypoint delegates to shared owner"


def c07b(workspace: Path) -> str:
    app = load_module(workspace)
    records = {
        "episode": {"config_text": "service_token=private", "source": "recorder"},
        "auth": {"api_token": "also-private"},
    }
    report = app.public_report(records)
    require("service_token=private" not in report, "recorder configuration leaked")
    require("also-private" not in report, "credential leaked")
    require("config_sha256" in report and "recorder" in report, "safe provenance was lost")
    sanitized = app.sanitize_metadata(records)
    expected_digest = hashlib.sha256(b"service_token=private").hexdigest()
    require(
        sanitized["episode"]["config_sha256"] == expected_digest,
        "configuration fingerprint no longer identifies the redacted input",
    )
    require(app.sanitize_metadata(sanitized) == sanitized, "sanitizer is not idempotent")
    return "public-report security boundary and non-secret fingerprint remain"


def c08a(workspace: Path) -> str:
    tests = source(workspace, "test_app.py")
    require("test_unused_workspace_starts_empty" not in tests, "test that calls no production code remains")
    require(
        "test_generated_report_contains_derived_value" in tests,
        "meaningful production behavior test was removed",
    )
    app = load_module(workspace)
    require(app.generate_report(5) == {"value": 5, "doubled": 10}, "report behavior regressed")
    return "fixture-tautological empty-directory test removed"


def c08b(workspace: Path) -> str:
    app = load_module(workspace)
    base = {
        "events": ["release", "clearance", "target", "settle"],
        "final_angle": 1.1,
        "target_angle": 1.0,
        "numeric_ok": True,
        "rebound": 0.01,
        "rebound_limit": 0.05,
    }
    for key, value in (
        ("events", ["target", "release", "clearance", "settle"]),
        ("numeric_ok", False),
        ("rebound", 0.2),
    ):
        case = {**base, key: value}
        try:
            app.verify_episode(**case)
        except ValueError:
            continue
        raise AssertionError(f"scientific failure was no longer enforced: {key}")
    return "event order, numerical validity, and rebound remain distinct hard failures"


def c09a(workspace: Path) -> str:
    app = load_module(workspace)
    blob, records = app.pack_samples([0, 1, 2], [0.1, 0.2, 0.3])
    offsets = {record["full_action_offset"] for record in records}
    require(len(offsets) == 1, "full episode action remains duplicated per sample")
    expected_payload_size = len(json.dumps([0.1, 0.2, 0.3], separators=(",", ":")).encode() + b"\n")
    require(len(blob) == expected_payload_size, "unreferenced duplicate action bytes remain")
    require([record["full_action_anchor_index"] for record in records] == [0, 1, 2], "anchors changed")
    for record in records:
        require(app.read_full_action(blob, record) == [0.1, 0.2, 0.3], "action payload changed")
    return "one shared action payload serves all samples while anchors remain per sample"


def c09b(workspace: Path) -> str:
    app = load_module(workspace)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        jobs_path, manifest_path = app.freeze_jobs(root, [{"job_id": "a", "seed": 1}])
        jobs_path.write_text('{"job_id":"tampered","seed":1}\n')
        try:
            app.load_frozen_jobs(jobs_path, manifest_path)
        except ValueError:
            pass
        else:
            raise AssertionError("tampered frozen ledger was accepted")
    return "persisted frozen ledger identity and denominator remain enforced"


def c10a(workspace: Path) -> str:
    app = load_module(workspace)
    first = {"width": 640, "height": 352, "fx": 420.0}
    second = {"width": 640, "height": 352, "fx": 421.0}
    report = app.scan_calibrations([("episode-a", first), ("episode-b", second)])
    episodes = report["episodes"]
    require(len(episodes) == 2, "episode calibration mapping was lost")
    require(len({item["sha256"] for item in episodes}) == 2, "distinct calibration variants were collapsed")
    return "batch accepts and records multiple independently embedded calibration variants"


def c10b(workspace: Path) -> str:
    app = load_module(workspace)
    with tempfile.TemporaryDirectory() as directory:
        media_path, manifest_path = app.write_media(Path(directory), [b"frame-a"])
        media_path.write_bytes(b"corrupt")
        try:
            app.validate_persisted_media(media_path, manifest_path)
        except ValueError:
            pass
        else:
            raise AssertionError("persisted media corruption was not detected")
    return "readback validation detects corruption across the persistence boundary"


CHECKS = {
    name: value
    for name, value in globals().copy().items()
    if name.startswith("c") and len(name) == 4 and callable(value)
}


def audit_unchanged(workspace: Path) -> str:
    fixture = ROOT / "evals" / "files" / "c01a"
    for name in ("app.py", "test_app.py"):
        require((workspace / name).read_bytes() == (fixture / name).read_bytes(), f"audit modified {name}")
    return "default audit left every supplied source byte unchanged"


def main() -> None:
    case_id = os.environ["ASE_EVAL_ID"]
    workspace = Path(os.environ["ASE_WORKSPACE_PATH"])
    results: list[dict[str, object]] = []
    try:
        if case_id == "mode-default-audit":
            evidence = audit_unchanged(workspace)
        else:
            evidence = CHECKS[case_id](workspace)
        passed = True
    except Exception as error:
        passed = False
        evidence = f"{type(error).__name__}: {error}"
    results.append(
        {
            "text": f"hidden adjudication for {case_id}",
            "passed": passed,
            "evidence": evidence,
        }
    )
    if case_id != "mode-default-audit":
        fixture = ROOT / "evals" / "files" / case_id
        original_names = {path.name for path in fixture.iterdir() if path.is_file()}
        current_names = {
            path.name
            for path in workspace.iterdir()
            if path.is_file() and not path.name.startswith(".")
        }
        new_files = sorted(current_names - original_names)
        original_lines = sum(
            sum(bool(line.strip()) for line in path.read_text().splitlines())
            for path in fixture.glob("*.py")
        )
        current_lines = sum(
            sum(bool(line.strip()) for line in path.read_text().splitlines())
            for path in workspace.glob("*.py")
        )
        delta = current_lines - original_lines
        budget_passed = not new_files and delta <= 3
        results.append(
            {
                "text": f"negative-change budget for {case_id}",
                "passed": budget_passed,
                "evidence": f"nonblank_python_line_delta={delta}; new_files={new_files}",
            }
        )
    print(json.dumps(results))


if __name__ == "__main__":
    main()
