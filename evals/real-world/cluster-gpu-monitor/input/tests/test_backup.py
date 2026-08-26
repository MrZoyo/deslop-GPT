"""SQLite 本地备份必须先自检并原子发布，失败时不得轮换旧成品。"""
from __future__ import annotations

import sqlite3
import stat
from types import SimpleNamespace

import pytest

from gpumon.db import backup


@pytest.fixture
def source_db(tmp_path, monkeypatch):
    path = tmp_path / "gpumon.db"
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE samples(id INTEGER PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO samples(value) VALUES ('first'), ('second')")
    conn.commit()
    conn.close()
    monkeypatch.setattr(backup, "db_path", lambda: path)
    return path


def _read_values(path):
    conn = sqlite3.connect(path)
    try:
        return [row[0] for row in conn.execute("SELECT value FROM samples ORDER BY id")]
    finally:
        conn.close()


def test_backup_is_checked_private_and_atomically_published(source_db):
    dest = backup.backup_now()

    assert dest.parent == source_db.parent / "backups"
    assert dest.name.startswith("gpumon_") and dest.suffix == ".db"
    assert stat.S_IMODE(dest.stat().st_mode) == 0o600
    assert _read_values(dest) == ["first", "second"]
    assert not list(dest.parent.glob("*.tmp"))

    conn = sqlite3.connect(dest)
    try:
        assert conn.execute("PRAGMA quick_check").fetchone() == ("ok",)
    finally:
        conn.close()


def test_explicit_backup_rejects_symlink_source(source_db, tmp_path):
    link = tmp_path / "linked.db"
    link.symlink_to(source_db)

    with pytest.raises(ValueError, match="symlink"):
        backup.backup_database(link)


def test_explicit_backup_rejects_symlink_destination(source_db, tmp_path):
    real_directory = tmp_path / "real-backups"
    real_directory.mkdir()
    linked_directory = tmp_path / "linked-backups"
    linked_directory.symlink_to(real_directory, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        backup.backup_database(source_db, directory=linked_directory)


def test_explicit_backup_supports_safe_custom_prefix(source_db, tmp_path):
    dest = backup.backup_database(
        source_db,
        directory=tmp_path / "maintenance-backups",
        prefix="gpumon_backfill",
    )

    assert dest.name.startswith("gpumon_backfill_")
    assert stat.S_IMODE(dest.stat().st_mode) == 0o600
    assert _read_values(dest) == ["first", "second"]


def test_quick_check_runs_on_temp_file_before_publish(source_db, monkeypatch):
    checked = []
    real_check = backup._quick_check

    def observe(path):
        checked.append(path)
        assert path.name.startswith(".") and path.name.endswith(".db.tmp")
        assert not any(path.parent.glob("gpumon_*.db"))
        real_check(path)

    monkeypatch.setattr(backup, "_quick_check", observe)
    dest = backup.backup_now()
    assert checked and dest.exists()


def test_failed_check_removes_temp_and_does_not_publish(source_db, monkeypatch):
    def fail_check(_path):
        raise sqlite3.DatabaseError("simulated check failure")

    monkeypatch.setattr(backup, "_quick_check", fail_check)
    with pytest.raises(sqlite3.DatabaseError, match="simulated"):
        backup.backup_now()

    directory = source_db.parent / "backups"
    assert not list(directory.glob("gpumon_*.db"))
    assert not list(directory.glob("*.tmp"))


def test_backup_failure_never_prunes_existing_completed_files(source_db, monkeypatch):
    directory = backup.backup_dir()
    old = directory / "gpumon_20000101_000000.db"
    old.write_bytes(b"previous-good-backup")

    def fail_check(_path):
        raise sqlite3.DatabaseError("simulated check failure")

    monkeypatch.setattr(backup, "_quick_check", fail_check)
    with pytest.raises(sqlite3.DatabaseError):
        backup.backup_and_prune(keep=1)
    assert old.read_bytes() == b"previous-good-backup"


def test_successful_backup_prunes_only_completed_db_files(source_db):
    directory = backup.backup_dir()
    oldest = directory / "gpumon_20000101_000000.db"
    newest = directory / "gpumon_20000102_000000.db"
    ignored_tmp = directory / ".gpumon_interrupted.db.tmp"
    oldest.write_bytes(b"oldest")
    newest.write_bytes(b"newest")
    ignored_tmp.write_bytes(b"partial")

    created, deleted = backup.backup_and_prune(keep=2)

    assert created.exists()
    assert deleted == [oldest]
    assert newest.exists()
    assert ignored_tmp.exists()
    assert backup.list_backups() == [created, newest]


def test_prune_rejects_delete_everything_value(source_db):
    completed = backup.backup_now()
    with pytest.raises(ValueError, match="1..1000"):
        backup.prune_old_backups(keep=0)
    assert completed.exists()


def test_disabled_setting_skips_only_scheduled_cli(monkeypatch, capsys):
    from gpumon import config
    from gpumon.cli import _cmd_backup

    monkeypatch.setattr(
        config,
        "load_settings",
        lambda: SimpleNamespace(backup=SimpleNamespace(enabled=False)),
    )

    def must_not_run():
        raise AssertionError("scheduled backup should have been skipped")

    monkeypatch.setattr(backup, "backup_and_prune", must_not_run)
    assert _cmd_backup(SimpleNamespace(scheduled=True)) == 0
    assert "跳过" in capsys.readouterr().out
