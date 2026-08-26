from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
INLINE_LINK = re.compile(r"!?\[[^\]]*\]\((?P<target>[^)\n]+)\)")


def _markdown_files() -> list[Path]:
    files = list(ROOT.glob("*.md"))
    for directory in (ROOT / "docs", ROOT / "deploy"):
        files.extend(directory.rglob("*.md"))
    return sorted(set(files))


def _link_path(raw_target: str) -> str | None:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1:target.index(">")]
    else:
        target = target.split(maxsplit=1)[0]

    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    return unquote(parsed.path)


def test_local_markdown_links_resolve_inside_repository():
    failures: list[str] = []
    root = ROOT.resolve()

    for document in _markdown_files():
        text = document.read_text(encoding="utf-8")
        for match in INLINE_LINK.finditer(text):
            relative = _link_path(match.group("target"))
            if relative is None:
                continue
            destination = (document.parent / relative).resolve()
            source = document.relative_to(ROOT)
            if not destination.is_relative_to(root):
                failures.append(f"{source}: link escapes repository: {relative}")
            elif not destination.exists():
                failures.append(f"{source}: missing link target: {relative}")

    assert not failures, "\n" + "\n".join(failures)
