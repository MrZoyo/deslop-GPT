"""数据库自动备份。

职责：
- 由 systemd timer 每天 04:00 触发
- 保留指定数量的备份（默认 3 个）
- 使用 SQLite backup API 在线写临时文件，自检、fsync 后再原子发布
"""
from __future__ import annotations

import os
import re
import sqlite3
import stat
from datetime import datetime
from pathlib import Path

from ..config import db_path, load_settings

_BACKUP_PREFIX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def backup_dir() -> Path:
    """备份目录：data/backups/"""
    d = db_path().parent / "backups"
    return _prepare_backup_dir(d)


def _prepare_backup_dir(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if directory.is_symlink() or not stat.S_ISDIR(directory.lstat().st_mode):
        raise ValueError(f"备份路径必须是普通目录且不能是 symlink: {directory}")
    os.chmod(directory, 0o700)
    return directory


def _regular_source(source: Path) -> Path:
    if source.is_symlink():
        raise ValueError(f"数据库不能是 symlink: {source}")
    try:
        source_stat = source.lstat()
    except FileNotFoundError:
        raise FileNotFoundError(f"数据库不存在: {source}") from None
    if not stat.S_ISREG(source_stat.st_mode):
        raise ValueError(f"数据库必须是普通文件: {source}")
    return source.resolve(strict=True)


def _quick_check(path: Path) -> None:
    uri = f"{path.resolve().as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        rows = [row[0] for row in conn.execute("PRAGMA quick_check")]
    finally:
        conn.close()
    if rows != ["ok"]:
        raise sqlite3.DatabaseError("临时备份 quick_check 未通过")


def _fsync_file(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _fsync_dir(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    fd = os.open(path, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _new_backup_paths(directory: Path, prefix: str = "gpumon") -> tuple[Path, Path]:
    """用微秒和 O_EXCL 避免并发手工备份覆盖同名成品。"""
    if not _BACKUP_PREFIX.fullmatch(prefix):
        raise ValueError("备份文件前缀不合法")
    for _ in range(100):
        ts = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
        dest = directory / f"{prefix}_{ts}.db"
        tmp = directory / f".{dest.name}.tmp"
        try:
            fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            continue
        os.close(fd)
        return dest, tmp
    raise FileExistsError("无法分配唯一的备份临时文件名")


def backup_database(source: str | Path, *, directory: str | Path | None = None,
                    prefix: str = "gpumon") -> Path:
    """安全备份任意显式 SQLite 普通文件，供受控维护脚本复用。"""
    src = _regular_source(Path(source))
    target_dir = _prepare_backup_dir(
        Path(directory) if directory is not None else src.parent / "backups"
    )
    dest, tmp = _new_backup_paths(target_dir, prefix)
    src_conn: sqlite3.Connection | None = None
    dest_conn: sqlite3.Connection | None = None
    try:
        # mode=ro 保证备份命令不会意外修改或创建源数据库。
        src_uri = f"{src.as_uri()}?mode=ro"
        src_conn = sqlite3.connect(src_uri, uri=True)
        dest_conn = sqlite3.connect(tmp)
        with dest_conn:
            src_conn.backup(dest_conn)
        dest_conn.close()
        dest_conn = None
        src_conn.close()
        src_conn = None

        _quick_check(tmp)
        os.chmod(tmp, 0o600)
        _fsync_file(tmp)
        os.replace(tmp, dest)
        _fsync_dir(target_dir)
    except BaseException:
        if dest_conn is not None:
            dest_conn.close()
        if src_conn is not None:
            src_conn.close()
        tmp.unlink(missing_ok=True)
        raise

    return dest


def backup_now() -> Path:
    """生成并原子发布一份经过 quick_check 的 0600 SQLite 在线备份。"""
    return backup_database(db_path(), directory=backup_dir())


def list_backups() -> list[Path]:
    """列出所有备份文件，按时间倒序（最新的在前）。"""
    backups = sorted(backup_dir().glob("gpumon_*.db"), reverse=True)
    return backups


def prune_old_backups(keep: int | None = None) -> list[Path]:
    """删除超过 keep 数量的旧备份，返回被删除的文件列表。

    keep 为 None 时从配置读取，默认 3。
    """
    if keep is None:
        keep = load_settings().backup.keep_count
    if not 1 <= keep <= 1000:
        raise ValueError("keep 必须在 1..1000 之间")
    backups = list_backups()
    to_delete = backups[keep:]
    for f in to_delete:
        f.unlink()
    return to_delete


def backup_and_prune(keep: int | None = None) -> tuple[Path, list[Path]]:
    """备份 + 清理旧备份，返回 (新备份路径, 被删除的备份列表)。

    keep 为 None 时从配置读取，默认 3。
    """
    new_backup = backup_now()
    deleted = prune_old_backups(keep)
    return new_backup, deleted
