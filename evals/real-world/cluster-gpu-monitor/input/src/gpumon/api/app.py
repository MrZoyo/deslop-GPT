"""FastAPI 应用：挂载 /api 路由 + 把 web/ 作为静态站点 serve。

只监听 127.0.0.1（见 settings/web）。对外访问一律经 Caddy 反代 + Basic Auth（阶段二）。
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .. import __version__
from ..config import CODE_ROOT
from .routes import router


class RevalidatingStaticFiles(StaticFiles):
    """可变前端资源允许缓存，但浏览器每次使用前必须向服务器确认版本。"""

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


def create_app(*, enable_docs: bool = False) -> FastAPI:
    docs_url = "/docs" if enable_docs else None
    openapi_url = "/openapi.json" if enable_docs else None
    redoc_url = "/redoc" if enable_docs else None
    application = FastAPI(
        title="GPU 集群占用监控",
        version=__version__,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )
    application.include_router(router)

    # web/ 目录作为静态站点；html=True 让 / 返回 index.html。必须在 API 路由之后挂载。
    web_dir = CODE_ROOT / "web"
    if web_dir.exists():
        application.mount(
            "/", RevalidatingStaticFiles(directory=str(web_dir), html=True), name="static"
        )
    return application


# 模块级 app 保持安全默认，供测试和通用 ASGI 导入；CLI 会按 settings 创建实例。
app = create_app()
