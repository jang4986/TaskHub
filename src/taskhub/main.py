import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from taskhub.api.v1.router import api_router
from taskhub.core.cache import close_redis
from taskhub.core.config import settings
from taskhub.db.session import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("taskhub")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up %s...", settings.PROJECT_NAME)
    yield
    logger.info("Shutting down %s...", settings.PROJECT_NAME)
    await engine.dispose()
    await close_redis()


app = FastAPI(
    title="TaskHub API",
    description="Task Management API with FastAPI, SQLAlchemy 2.x Async, PostgreSQL & Redis",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    components = openapi_schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})
    security_schemes["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Nhập JWT access token theo định dạng: Bearer <token>",
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore[method-assign]

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
