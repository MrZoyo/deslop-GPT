"""演示数据工具的防误删、防误导出边界。

这些脚本会覆盖数据库/清单，静态导出还会递归删除输出目录。这里集中维护路径保护与
生成标记，避免两个 CLI 各写一套稍有差异的安全判断。
"""
from __future__ import annotations

import os
import sqlite3
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DEMO_DB_MARKER = "cluster-gpu-monitor:synthetic-demo:v1"
DEMO_DB_MARKER_TABLE = "gpumon_demo_metadata"
DEMO_INVENTORY_MARKER = "# gpumon-synthetic-demo-inventory: v1"
STATIC_OUTPUT_MARKER_NAME = ".gpumon-static-demo"
STATIC_OUTPUT_MARKER = "cluster-gpu-monitor:static-demo:v1\n"


class DemoSafetyError(ValueError):
    """演示工具检测到可能破坏或泄漏真实数据的目标。"""


def resolve_cli_path(value: str | Path, *, base: Path = REPO_ROOT) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve(strict=False)


def _runtime_roots() -> set[Path]:
    roots = {REPO_ROOT}
    configured = os.environ.get("GPUMON_ROOT")
    if configured:
        roots.add(resolve_cli_path(configured))

    # 与 gpumon.config.find_root() 的开发态规则保持一致：submodule 上层可能才放着
    # 私有真实配置。只检查固定祖先路径，不递归扫描文件树。
    for parent in (REPO_ROOT, *REPO_ROOT.parents):
        if (parent / "config" / "inventory.yaml").is_file():
            roots.add(parent.resolve())
            break
    return roots


def _protected_runtime_files() -> set[Path]:
    protected: set[Path] = {
        (REPO_ROOT / "config" / "inventory.example.yaml").resolve(),
        (REPO_ROOT / "config" / "settings.example.toml").resolve(),
    }
    for root in _runtime_roots():
        inventory = (root / "config" / "inventory.yaml").resolve(strict=False)
        settings = (root / "config" / "settings.toml").resolve(strict=False)
        protected.update({inventory, settings, (root / "data" / "gpumon.db").resolve(strict=False)})
        if not settings.is_file():
            continue
        try:
            with settings.open("rb") as handle:
                configured_db = tomllib.load(handle).get("db", {}).get("path")
            if isinstance(configured_db, str) and configured_db:
                db_path = Path(configured_db)
                if not db_path.is_absolute():
                    db_path = root / db_path
                protected.add(db_path.resolve(strict=False))
        except (OSError, tomllib.TOMLDecodeError):
            # 配置本身损坏时仍保护固定默认位置；错误由正常配置校验报告。
            pass
    return protected


def assert_safe_generation_target(path: Path, *, kind: str) -> Path:
    """校验 generator 将创建/覆盖的单个文件目标。"""
    path = resolve_cli_path(path)
    if path == Path(path.anchor) or path in {Path.home().resolve(), REPO_ROOT}:
        raise DemoSafetyError(f"拒绝把 {kind} 写到危险路径: {path}")
    if path.exists() and path.is_dir():
        raise DemoSafetyError(f"{kind} 目标是目录，拒绝覆盖: {path}")
    if path in _protected_runtime_files():
        raise DemoSafetyError(f"拒绝覆盖真实运行文件或仓库示例: {path}")
    if kind == "database" and path.name == "gpumon.db":
        raise DemoSafetyError("演示数据库不能使用真实库名 gpumon.db")
    if kind == "inventory" and path.name in {"inventory.yaml", "settings.toml"}:
        raise DemoSafetyError(f"演示清单不能使用真实配置名 {path.name}")
    return path


def assert_safe_export_input(path: Path, *, kind: str) -> Path:
    """拒绝直接把已知真实运行文件交给静态导出器。"""
    path = resolve_cli_path(path)
    if not path.is_file():
        raise DemoSafetyError(f"{kind} 输入不存在或不是普通文件: {path}")
    # 公开 settings.example.toml 正是 demo 导出的无秘密默认配置；它禁止被 generator
    # 覆盖，但允许只读输入。其余真实/示例文件继续保护。
    allowed_example = (
        kind == "settings"
        and path == (REPO_ROOT / "config" / "settings.example.toml").resolve()
    )
    if path in _protected_runtime_files() and not allowed_example:
        raise DemoSafetyError(f"拒绝读取真实运行文件进行公开静态导出: {path}")
    if kind == "database" and path.name == "gpumon.db":
        raise DemoSafetyError("拒绝导出名为 gpumon.db 的数据库；请使用带生成标记的 demo 库")
    if kind == "inventory" and path.name == "inventory.yaml":
        raise DemoSafetyError("拒绝导出真实 inventory.yaml")
    if kind == "settings" and path.name == "settings.toml":
        raise DemoSafetyError("拒绝使用真实 settings.toml 生成公开静态站点")
    return path


def assert_safe_export_directory(path: Path) -> Path:
    """校验会被 ``shutil.rmtree`` 的静态站点输出目录。"""
    raw = Path(path).expanduser()
    if not raw.is_absolute():
        raw = REPO_ROOT / raw
    if raw.is_symlink():
        raise DemoSafetyError(f"输出目录本身是符号链接，拒绝递归删除: {raw}")
    path = raw.resolve(strict=False)
    if path == Path(path.anchor):
        raise DemoSafetyError("拒绝把文件系统根目录作为静态导出目标")

    # 目标不能等于、也不能成为 home/仓库/运行根的祖先，否则 --force 会删掉整棵树。
    protected_roots = {Path.home().resolve(), *_runtime_roots()}
    for protected in protected_roots:
        if path == protected or protected.is_relative_to(path):
            raise DemoSafetyError(f"输出目录会覆盖关键目录: {path}")

    # 仓库里的 dist/、data/ 可承载生成物；源码、配置和版本控制目录绝不能成为目标，
    # 包括它们的子目录，避免例如 --out web/js --force 删除前端源码。
    for name in (".git", ".github", "config", "deploy", "docs", "scripts", "src", "tests", "web"):
        protected = (REPO_ROOT / name).resolve(strict=False)
        if path == protected or path.is_relative_to(protected):
            raise DemoSafetyError(f"输出目录落在仓库受保护区域: {path}")
    return path


def safe_child(base: Path, relative: str | Path) -> Path:
    """在 base 内解析生成文件，拒绝绝对路径和 ``..`` 逃逸。"""
    base = base.resolve(strict=False)
    relative = Path(relative)
    if relative.is_absolute() or ".." in relative.parts:
        raise DemoSafetyError(f"生成文件名试图逃逸输出目录: {relative}")
    child = (base / relative).resolve(strict=False)
    if not child.is_relative_to(base):
        raise DemoSafetyError(f"生成文件不在输出目录内: {relative}")
    return child


def initialize_demo_database_marker(conn: sqlite3.Connection) -> None:
    """给新 demo 库写入 building 标记；失败的生成可安全重跑，但不能被导出。"""
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {DEMO_DB_MARKER_TABLE} ("
        "key TEXT PRIMARY KEY, value TEXT NOT NULL) WITHOUT ROWID"
    )
    conn.executemany(
        f"INSERT OR REPLACE INTO {DEMO_DB_MARKER_TABLE}(key,value) VALUES(?,?)",
        (("marker", DEMO_DB_MARKER), ("state", "building")),
    )
    conn.commit()


def finalize_demo_database(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        row = conn.execute(
            f"SELECT value FROM {DEMO_DB_MARKER_TABLE} WHERE key='marker'"
        ).fetchone()
        if row is None or row[0] != DEMO_DB_MARKER:
            raise DemoSafetyError("拒绝完成没有正确生成标记的数据库")
        conn.execute(
            f"INSERT OR REPLACE INTO {DEMO_DB_MARKER_TABLE}(key,value) VALUES('state','complete')"
        )
        conn.commit()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")


def demo_database_state(path: Path) -> str | None:
    """返回带正确标记的 demo DB 状态；普通/损坏/不可读 DB 返回 None。"""
    path = resolve_cli_path(path)
    if not path.is_file():
        return None
    try:
        uri = f"{path.as_uri()}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=2) as conn:
            rows = dict(conn.execute(
                f"SELECT key,value FROM {DEMO_DB_MARKER_TABLE} WHERE key IN ('marker','state')"
            ))
        if rows.get("marker") != DEMO_DB_MARKER:
            return None
        return rows.get("state")
    except (OSError, sqlite3.Error):
        return None


def is_demo_inventory(path: Path) -> bool:
    path = resolve_cli_path(path)
    try:
        with path.open("r", encoding="utf-8") as handle:
            return handle.readline().rstrip("\n\r") == DEMO_INVENTORY_MARKER
    except OSError:
        return False


def static_output_is_marked(path: Path) -> bool:
    marker = safe_child(path, STATIC_OUTPUT_MARKER_NAME)
    try:
        return marker.read_text(encoding="utf-8") == STATIC_OUTPUT_MARKER
    except OSError:
        return False


def mark_static_output(path: Path) -> None:
    safe_child(path, STATIC_OUTPUT_MARKER_NAME).write_text(
        STATIC_OUTPUT_MARKER, encoding="utf-8"
    )
