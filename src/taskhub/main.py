import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from taskhub.api.v1.router import api_router
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


app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
