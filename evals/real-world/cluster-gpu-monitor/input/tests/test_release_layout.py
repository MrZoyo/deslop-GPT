"""release/state 分离、systemd 调度与浏览器防护的静态契约。"""
import hashlib
import tomllib
from pathlib import Path

from gpumon import __version__
from gpumon.api.app import create_app
from gpumon.config import CODE_ROOT

ROOT = Path(__file__).resolve().parents[1]


def test_release_version_identifiers_match():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    locked_project = next(
        package
        for package in lock["package"]
        if package["name"] == project["project"]["name"]
        and package.get("source") == {"editable": "."}
    )

    assert __version__ == project["project"]["version"]
    assert locked_project["version"] == __version__
    assert create_app().version == __version__


def test_code_root_owns_web_assets_independently_of_state_root():
    assert CODE_ROOT == ROOT
    assert (CODE_ROOT / "web" / "index.html").is_file()


def test_system_units_execute_through_current_release():
    unit_dir = ROOT / "deploy" / "systemd"
    for name in (
        "system-gpumon-collector.service",
        "system-gpumon-web.service",
        "gpumon-backup.service",
    ):
        text = (unit_dir / name).read_text(encoding="utf-8")
        assert "WorkingDirectory=__ROOT__/current" in text
        assert "Environment=GPUMON_ROOT=__ROOT__" in text
        assert "ExecStart=__ROOT__/current/.venv/bin/gpumon" in text
        assert "/opt/gpu-monitor" not in text

    for name in ("system-gpumon-collector.service", "gpumon-backup.service"):
        text = (unit_dir / name).read_text(encoding="utf-8")
        assert "User=__USER__" in text
        assert "Group=__GROUP__" in text


def test_backup_timer_has_exactly_one_schedule_and_no_eager_service_dependency():
    text = (ROOT / "deploy" / "systemd" / "gpumon-backup.timer").read_text(
        encoding="utf-8"
    )
    assert text.count("OnCalendar=") == 1
    assert "OnCalendar=*-*-* 04:00:00" in text
    assert "OnCalendar=daily" not in text
    assert "Requires=gpumon-backup.service" not in text


def test_system_web_unit_is_a_separate_read_only_sandbox():
    text = (
        ROOT / "deploy" / "systemd" / "system-gpumon-web.service"
    ).read_text(encoding="utf-8")

    assert "User=__WEB_USER__" in text
    assert "Group=__GROUP__" in text
    assert "User=__USER__" not in text
    for setting in (
        "NoNewPrivileges=true",
        "PrivateTmp=true",
        "PrivateDevices=true",
        "ProtectSystem=strict",
        "ProtectHome=true",
        "ReadOnlyPaths=__ROOT__",
        "IPAddressAllow=localhost",
        "IPAddressDeny=any",
    ):
        assert setting in text
    assert "ReadWritePaths=" not in text


def test_collector_units_have_memory_and_task_circuit_breakers():
    unit_dir = ROOT / "deploy" / "systemd"
    for name in ("gpumon-collector.service", "system-gpumon-collector.service"):
        text = (unit_dir / name).read_text(encoding="utf-8")
        assert "MemoryHigh=384M" in text
        assert "MemoryMax=512M" in text
        assert "TasksMax=128" in text


def test_system_web_unit_has_memory_and_task_circuit_breakers():
    text = (
        ROOT / "deploy" / "systemd" / "system-gpumon-web.service"
    ).read_text(encoding="utf-8")

    assert "MemoryHigh=256M" in text
    assert "MemoryMax=384M" in text
    assert "TasksMax=64" in text


def test_caddy_template_sets_browser_security_headers_and_no_store():
    text = (ROOT / "deploy" / "caddy" / "Caddyfile.example").read_text(
        encoding="utf-8"
    )
    for header in (
        "Content-Security-Policy",
        "Strict-Transport-Security",
        "X-Content-Type-Options",
        "Referrer-Policy",
        "Permissions-Policy",
        "X-Frame-Options",
        "Cache-Control",
    ):
        assert header in text
    assert "frame-ancestors 'none'" in text
    assert "script-src 'self'" in text
    assert "@gpumon_no_store path / /index.html /api/*" in text
    assert "admin off" in text


def test_pages_meta_csp_and_vendored_echarts_are_pinned():
    index = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert 'http-equiv="Content-Security-Policy"' in index
    assert "script-src 'self'" in index
    assert "unsafe-eval" not in index
    assert 'echarts.min.js?v=6.1.0' in index

    bundle = ROOT / "web" / "vendor" / "echarts.min.js"
    assert hashlib.sha256(bundle.read_bytes()).hexdigest() == (
        "b66b25aeb4df84e33199dc21694014d336d222cbd9deb0e5a7c14bd6aa0d0fd0"
    )
    assert (ROOT / "web" / "vendor" / "ECHARTS-LICENSE.txt").is_file()
    assert (ROOT / "web" / "vendor" / "ECHARTS-NOTICE.txt").is_file()
