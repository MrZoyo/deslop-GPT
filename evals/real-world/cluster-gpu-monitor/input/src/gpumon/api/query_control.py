"""Web 查询的并发和超时错误边界。"""
from __future__ import annotations

import math
import sqlite3
import threading
from dataclasses import dataclass
from functools import wraps

from fastapi import HTTPException

from ..config import load_settings


@dataclass
class _QueryGate:
    concurrency: int
    wait_s: float
    semaphore: threading.BoundedSemaphore


_gate_lock = threading.Lock()
_gate: _QueryGate | None = None


def _get_query_gate() -> _QueryGate:
    global _gate
    web = load_settings().web
    key = (web.max_query_concurrency, web.query_queue_timeout_s)
    with _gate_lock:
        if _gate is None or (_gate.concurrency, _gate.wait_s) != key:
            _gate = _QueryGate(
                concurrency=web.max_query_concurrency,
                wait_s=web.query_queue_timeout_s,
                semaphore=threading.BoundedSemaphore(web.max_query_concurrency),
            )
        return _gate


def _retry_after(wait_s: float) -> str:
    return str(max(1, math.ceil(wait_s)))


def bounded_query(func):
    """限制昂贵 HTTP 查询并把 SQLite 主动中断转换为通用 503。"""

    @wraps(func)
    def wrapped(*args, **kwargs):
        gate = _get_query_gate()
        acquired = gate.semaphore.acquire(timeout=gate.wait_s)
        if not acquired:
            raise HTTPException(
                status_code=503,
                detail="查询繁忙，请稍后重试",
                headers={"Retry-After": _retry_after(gate.wait_s)},
            )
        try:
            return func(*args, **kwargs)
        except sqlite3.OperationalError as exc:
            if "interrupted" in str(exc).lower():
                raise HTTPException(
                    status_code=503,
                    detail="查询超过服务器时间上限，请稍后重试",
                    headers={"Retry-After": "1"},
                ) from None
            raise
        finally:
            gate.semaphore.release()

    return wrapped


def _reset_query_gate_for_tests() -> None:
    global _gate
    with _gate_lock:
        _gate = None
