"""Docker 部署必须保留原生部署已经建立的权限边界。"""
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _compose() -> dict:
    return yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))


def _mounts(service: dict) -> dict[str, dict]:
    return {mount["target"]: mount for mount in service["volumes"]}


def test_docker_build_context_is_an_explicit_source_allowlist():
    patterns = [
        line.strip()
        for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert patterns[0] == "**"
    assert "!src/**" in patterns
    assert "!web/**" in patterns
    assert "!config/**" not in patterns
    assert "!data/**" not in patterns


def test_image_runs_as_non_root_and_contains_runtime_dependencies():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "openssh-client" in dockerfile
    assert "uv sync --frozen --no-dev" in dockerfile
    assert "COPY src ./src" in dockerfile
    assert "COPY web ./web" in dockerfile
    assert "USER gpumon:gpumon" in dockerfile
    assert "STOPSIGNAL SIGINT" in dockerfile
    assert 'ENTRYPOINT ["gpumon"]' in dockerfile


def test_compose_separates_collector_web_and_backup_permissions():
    compose = _compose()
    services = compose["services"]
    assert set(services) == {"collector", "web", "backup"}

    collector_mounts = _mounts(services["collector"])
    web_mounts = _mounts(services["web"])
    backup_mounts = _mounts(services["backup"])

    assert collector_mounts["/home/gpumon/.ssh"]["read_only"] is True
    assert "/home/gpumon/.ssh" not in web_mounts
    assert "/home/gpumon/.ssh" not in backup_mounts

    assert collector_mounts["/state/config"]["read_only"] is True
    assert web_mounts["/state/config"]["read_only"] is True
    assert backup_mounts["/state/config"]["read_only"] is True

    assert "read_only" not in collector_mounts["/state/data"]
    assert web_mounts["/state/data"]["read_only"] is True
    assert "read_only" not in backup_mounts["/state/data"]
    assert services["backup"]["network_mode"] == "none"


def test_compose_applies_runtime_circuit_breakers():
    services = _compose()["services"]

    expected = {
        "collector": ("512m", 128),
        "web": ("384m", 64),
        "backup": ("384m", 32),
    }
    for name, (memory, pids) in expected.items():
        service = services[name]
        assert service["read_only"] is True
        assert service["cap_drop"] == ["ALL"]
        assert service["security_opt"] == ["no-new-privileges:true"]
        assert service["mem_limit"] == memory
        assert service["pids_limit"] == pids


def test_web_is_loopback_only_and_has_no_egress_network():
    compose = _compose()
    web = compose["services"]["web"]
    port = web["ports"][0]

    assert port["host_ip"] == "${GPUMON_WEB_BIND:-127.0.0.1}"
    assert port["target"] == 8848
    assert web["networks"] == ["web-internal"]
    assert compose["networks"]["web-internal"]["internal"] is True
    assert web["command"] == ["web", "--host", "0.0.0.0", "--port", "8848"]


def test_only_collector_receives_an_egress_network():
    services = _compose()["services"]

    assert services["collector"]["networks"] == ["collector-egress"]
    assert services["web"]["networks"] == ["web-internal"]
    assert "networks" not in services["backup"]
