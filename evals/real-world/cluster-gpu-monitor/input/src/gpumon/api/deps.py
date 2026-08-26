"""API 共享依赖：Store 单例、使用人打码、窗口校验。"""
from __future__ import annotations

from functools import lru_cache

from ..config import load_settings
from ..db.store import METRICS, SCOPES, USER_TOP_SORTS, WINDOWS, Store


@lru_cache(maxsize=1)
def get_store() -> Store:
    # Web/API 进程只负责查询。mode=ro + query_only 让代码路径本身也无法修改数据库，
    # 不把安全性只寄托在部署机的文件权限上。
    return Store(
        read_only=True,
        query_timeout_s=load_settings().web.query_timeout_s,
    )


def mask_username(name: str | None) -> str | None:
    """privacy.mask_users 开启时把用户名打码：djr→d*r, Lyle→L**e。"""
    if not name or not load_settings().privacy.mask_users:
        return name
    if len(name) <= 2:
        return name[0] + "*"
    return name[0] + "*" * (len(name) - 2) + name[-1]


def valid_window(window: str) -> str:
    return _valid_choice(window, WINDOWS, "窗口")


def valid_scope(scope: str) -> str:
    return _valid_choice(scope, SCOPES, "scope")


def valid_metric(metric: str) -> str:
    return _valid_choice(metric, METRICS, "指标")


def valid_user_sort(by: str) -> str:
    return _valid_choice(by, USER_TOP_SORTS, "排序字段")


def valid_series_id(scope: str, entity_id: int | None) -> int | None:
    from fastapi import HTTPException

    if scope == "global":
        if entity_id is not None:
            raise HTTPException(400, "global scope 不接受 id")
    elif entity_id is None:
        raise HTTPException(400, f"{scope} scope 必须提供正整数 id")
    return entity_id


def _valid_choice(value: str, choices, label: str) -> str:
    if value not in choices:
        from fastapi import HTTPException
        raise HTTPException(400, f"未知{label} {value}，可选 {list(choices)}")
    return value
