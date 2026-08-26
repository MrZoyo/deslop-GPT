#!/usr/bin/env python3
"""只检查 Git 新增行中的凭据特征，输出不回显匹配内容。"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(
    os.environ.get("GPUMON_SECRET_SCAN_ROOT", Path(__file__).resolve().parents[1])
).resolve(strict=True)
DEFAULT_BASELINE = ROOT / ".secret-scan-baseline.json"
REVISION = re.compile(r"^(?!-)[A-Za-z0-9][A-Za-z0-9._/@{}^~+-]{0,255}$")
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")

ASSIGNMENT = re.compile(
    r"(?ix)\b(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|"
    r"client[_-]?secret|credential|sshpass|basic[_-]?hash)\b\s*[:=]\s*"
    r"(?P<value>\"[^\"\n]+\"|'[^'\n]+'|[^\s#;,]+)"
)
SSHPASS = re.compile(
    r"(?ix)\bsshpass\b.*?(?:-p\s+|--password(?:=|\s+))"
    r"(?P<value>\"[^\"\n]+\"|'[^'\n]+'|[^\s#;,]+)"
)
BEARER = re.compile(
    r"(?ix)\b(?:authorization\s*:\s*bearer|bearer)\s+"
    r"(?P<value>[A-Za-z0-9._~+/=-]{12,})"
)
URL_CREDENTIAL = re.compile(
    r"(?i)\b[a-z][a-z0-9+.-]*://[^\s/:@]+:(?P<value>[^\s/@]{6,})@"
)
PASSWORD_LABEL = re.compile(
    r"(?i)(?:密码|password|passwd)\s*[:：]\s*(?P<value>[^\s\"'<>]{6,})"
)
TOKEN_FORMATS = (
    ("github-token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("private-key", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY-----")),
)


def _run_git(*args: str, input_bytes: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        input=input_bytes,
        check=True,
        capture_output=True,
    ).stdout


def _resolve_revision(value: str) -> str:
    if not REVISION.fullmatch(value):
        raise ValueError(f"非法 git revision: {value!r}")
    return _run_git("rev-parse", "--verify", f"{value}^{{object}}").decode().strip()


def _placeholder(value: str) -> bool:
    cleaned = value.strip().strip("'\"").strip()
    lowered = cleaned.lower()
    if not cleaned:
        return True
    if any(marker in cleaned for marker in ("<", ">", "${", "{{", "}}", "...", "***")):
        return True
    if cleaned.startswith("$") or lowered.startswith(("env:", "example_", "your_")):
        return True
    normalized = re.sub(r"[^a-z0-9]+", "", lowered)
    return normalized in {
        "changeme", "dummy", "example", "placeholder", "redacted",
        "replace", "replaceit", "secret", "testsecret", "yourpassword",
    }


def _rules(line: str) -> set[str]:
    found: set[str] = set()
    for rule, pattern in TOKEN_FORMATS:
        if pattern.search(line):
            found.add(rule)
    for rule, pattern in (
        ("credential-assignment", ASSIGNMENT),
        ("sshpass-password", SSHPASS),
        ("bearer-token", BEARER),
        ("url-credential", URL_CREDENTIAL),
        ("password-label", PASSWORD_LABEL),
    ):
        for match in pattern.finditer(line):
            value = match.groupdict().get("value", match.group(0))
            if not _placeholder(value):
                found.add(rule)
    return found


def _line_hash(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8", errors="surrogateescape")).hexdigest()


def _load_baseline(path: Path) -> set[tuple[str, str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"缺少 secret baseline: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != 1 or not isinstance(payload.get("accepted"), list):
        raise ValueError("secret baseline 格式错误")
    accepted = set()
    for item in payload["accepted"]:
        accepted.add((item["path"], item["sha256"], item["rule"]))
    return accepted


def _safe_path(path: str) -> str:
    return "".join(char if char.isprintable() else "?" for char in path)


def _parse_added_lines(patch: str):
    path: str | None = None
    line_number: int | None = None
    for line in patch.splitlines():
        if line.startswith("+++ "):
            path = line[4:]
            if path.startswith("b/"):
                path = path[2:]
            line_number = None
            continue
        hunk = HUNK.match(line)
        if hunk:
            line_number = int(hunk.group(1))
            continue
        if path is None or line_number is None:
            continue
        if line.startswith("+") and not line.startswith("+++"):
            yield path, line_number, line[1:]
            line_number += 1
        elif line.startswith(" "):
            line_number += 1
        elif line.startswith("-") or line == r"\ No newline at end of file":
            continue


def _added_lines(base: str, head: str):
    base_sha = _resolve_revision(base)
    head_sha = _resolve_revision(head)
    patch = _run_git(
        "-c", "core.quotePath=false", "diff", "--no-ext-diff", "--no-color",
        "--unified=0", "--diff-filter=ACMR", base_sha, head_sha, "--",
    ).decode("utf-8", errors="surrogateescape")
    yield from _parse_added_lines(patch)


def _staged_lines():
    patch = _run_git(
        "-c", "core.quotePath=false", "diff", "--cached", "--no-ext-diff",
        "--no-color", "--unified=0", "--diff-filter=ACMR", "--",
    ).decode("utf-8", errors="surrogateescape")
    yield from _parse_added_lines(patch)


def _scan(lines, baseline_path: Path) -> int:
    baseline = _load_baseline(baseline_path)
    findings = []
    for path, line_number, line in lines:
        digest = _line_hash(line)
        for rule in _rules(line):
            if (path, digest, rule) not in baseline:
                findings.append((path, line_number, rule))
    for path, line_number, rule in findings:
        print(f"疑似新增凭据: {_safe_path(path)}:{line_number} [{rule}]", file=sys.stderr)
    if findings:
        print(f"共发现 {len(findings)} 项；输出已省略匹配内容。", file=sys.stderr)
        return 1
    print("新增行凭据扫描通过（未回显文件内容）。")
    return 0


def _generate_baseline(paths: list[str]) -> int:
    accepted = []
    for raw_path in paths:
        path = (ROOT / raw_path).resolve(strict=True)
        try:
            tracked = path.relative_to(ROOT).as_posix()
        except ValueError:
            raise ValueError(f"baseline 文件必须位于仓库内: {raw_path}") from None
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"baseline 目标必须是普通文件: {raw_path}")
        for line in path.read_text(encoding="utf-8", errors="surrogateescape").splitlines():
            digest = _line_hash(line)
            for rule in sorted(_rules(line)):
                accepted.append({"path": tracked, "sha256": digest, "rule": rule})
    print(json.dumps({"version": 1, "accepted": accepted}, indent=2, sort_keys=True))
    return 0


def _self_test() -> int:
    cases = {
        "password = '<password>'": set(),
        "password = '${PASSWORD}'": set(),
        "password = 'correct horse battery staple'": {"credential-assignment"},
        "echo '密码: real-password-123'": {"password-label"},
        "sshpass -p 'real-password-123' ssh host": {"sshpass-password"},
        "Authorization: Bearer abcdefghijklmnopqrstuvwxyz": {"bearer-token"},
        "-----BEGIN OPENSSH PRIVATE KEY-----": {"private-key"},
    }
    for line, expected in cases.items():
        actual = _rules(line)
        if actual != expected:
            print(f"自检失败: expected={expected}, actual={actual}", file=sys.stderr)
            return 2
    print("secret scanner 自检通过。")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--generate-baseline", nargs="+")
    args = parser.parse_args()
    try:
        if args.self_test:
            return _self_test()
        if args.generate_baseline:
            return _generate_baseline(args.generate_baseline)
        if args.staged:
            return _scan(_staged_lines(), args.baseline.resolve())
        if not args.base:
            parser.error("扫描必须提供 --base")
        return _scan(_added_lines(args.base, args.head), args.baseline.resolve())
    except (FileNotFoundError, json.JSONDecodeError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"secret scanner 失败: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
