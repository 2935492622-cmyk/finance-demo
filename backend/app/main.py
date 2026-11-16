from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import get_engine
from .exceptions import register_exception_handlers
from .routers import health, transactions


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    if get_engine.cache_info().currsize:
        get_engine().dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="个人记账 Demo API", version="0.1.0", lifespan=lifespan)
    register_exception_handlers(app)
    app.include_router(transactions.router)
    app.include_router(health.router)
    return app


app = create_app()
