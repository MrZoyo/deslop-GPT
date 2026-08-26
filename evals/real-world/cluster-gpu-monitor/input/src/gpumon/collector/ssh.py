"""通过系统 ssh 异步采集一台主机的原始探测输出。

为什么用系统 ssh 而非 paramiko：直接复用 ~/.ssh/config 的别名、ProxyJump、密钥、
known_hosts，代码里不出现任何 IP/端口/key。换部署机只需改 ssh config + inventory。
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from ..config import load_settings
from ..models import ProbeResult
from .parse import parse_probe

_PROBE_TEMPLATE = Path(__file__).with_name("remote_probe.sh")
_READ_CHUNK_BYTES = 64 * 1024


class OutputLimitExceeded(RuntimeError):
    """SSH stdout/stderr 的合计字节数超过单轮预算。"""


class _OutputBudget:
    def __init__(self, limit: int):
        self.limit = limit
        self.remaining = limit

    def claim(self, size: int) -> None:
        # asyncio 协程只会在 await 处切换；这里同步检查并扣减，两个 reader 共用也不会竞态。
        if size > self.remaining:
            raise OutputLimitExceeded(f"SSH 输出超过 {self.limit} 字节")
        self.remaining -= size


async def _kill_process(proc: asyncio.subprocess.Process) -> None:
    if proc.returncode is None:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
    try:
        await proc.wait()
    except ProcessLookupError:
        pass


async def _read_limited(
    reader: asyncio.StreamReader,
    budget: _OutputBudget,
) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = await reader.read(_READ_CHUNK_BYTES)
        if not chunk:
            return b"".join(chunks)
        budget.claim(len(chunk))
        chunks.append(chunk)


async def _feed_stdin(writer: asyncio.StreamWriter, data: bytes) -> None:
    try:
        writer.write(data)
        await writer.drain()
    except (BrokenPipeError, ConnectionResetError):
        # 远端可能在脚本写完前就退出；返回码/stderr 会给出真正原因。
        pass
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except (BrokenPipeError, ConnectionResetError):
            pass


async def _communicate_limited(
    proc: asyncio.subprocess.Process,
    data: bytes,
    limit: int,
) -> tuple[bytes, bytes]:
    """并发排空两个 pipe，但 stdout+stderr 最多只在内存中保留 ``limit`` 字节。"""
    assert proc.stdin is not None and proc.stdout is not None and proc.stderr is not None
    budget = _OutputBudget(limit)
    stdout_task = asyncio.create_task(_read_limited(proc.stdout, budget))
    stderr_task = asyncio.create_task(_read_limited(proc.stderr, budget))
    stdin_task = asyncio.create_task(_feed_stdin(proc.stdin, data))
    tasks = (stdout_task, stderr_task, stdin_task)
    try:
        out, err, _ = await asyncio.gather(*tasks)
        await proc.wait()
        return out, err
    except BaseException:
        # 包括 wait_for 注入的 CancelledError：任何非正常退出都不能遗留 ssh 子进程。
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await _kill_process(proc)
        raise


def _failed(host_key: str, message: str) -> ProbeResult:
    return ProbeResult(host_key=host_key, ok=False, error=message[:512])


def _build_script(vendor_hint: str | None = None) -> str:
    gap = load_settings().collector.cpu_sample_gap_s
    # vendor 只允许白名单值：这段字符串会被塞进远端 shell 变量赋值，
    # 不做校验等于把 inventory 的任意内容送去远端执行。
    hint = vendor_hint if vendor_hint in ("nvidia", "amd") else ""
    return (_PROBE_TEMPLATE.read_text(encoding="utf-8")
            .replace("__CPU_GAP__", str(int(gap)))
            .replace("__VENDOR_HINT__", hint))


def _ssh_opts() -> list[str]:
    c = load_settings().collector
    return [
        "-o", "BatchMode=yes",
        "-o", f"ConnectTimeout={c.ssh_connect_timeout_s}",
        "-o", "ServerAliveInterval=5",
        "-o", "ServerAliveCountMax=2",
        # 主机密钥策略由每个 ~/.ssh/config alias 决定；不同资产的现实条件不同。
        "-o", "ForwardAgent=no",
        "-o", "ForwardX11=no",
        "-o", "RequestTTY=no",
        "-o", "ClearAllForwardings=yes",
        "-o", "PermitLocalCommand=no",
    ]


async def probe(host_key: str, ssh_alias: str, vendor: str | None = None) -> ProbeResult:
    """采集一台主机；任何失败都收敛成 ok=False 的 ProbeResult，绝不抛给上层。

    vendor 来自 inventory（可选）：给了就跳过远端自动探测，异构机房里更稳。
    """
    script = _build_script(vendor).encode()
    collector = load_settings().collector
    total_timeout = collector.ssh_total_timeout_s
    output_limit = collector.ssh_output_limit_bytes
    argv = ["ssh", *_ssh_opts(), ssh_alias, "bash", "-s"]
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except Exception as e:  # ssh 不存在等
        return _failed(host_key, f"启动 ssh 失败: {e}")

    try:
        out, err = await asyncio.wait_for(
            _communicate_limited(proc, script, output_limit),
            timeout=total_timeout,
        )
    except TimeoutError:
        return _failed(host_key, f"超时(>{total_timeout}s)")
    except OutputLimitExceeded:
        return _failed(host_key, f"SSH 输出超过上限({output_limit} bytes)")
    except Exception as e:
        return _failed(host_key, f"ssh 异常: {e}")

    if proc.returncode != 0:
        msg = (err.decode(errors="replace").strip() or f"ssh 返回码 {proc.returncode}")
        return _failed(host_key, msg[:500])

    try:
        return parse_probe(host_key, out.decode(errors="replace"))
    except Exception as e:
        return _failed(host_key, f"解析失败: {e}")
