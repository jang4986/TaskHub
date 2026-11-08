"""TaskHub - Task Management API."""
import uvicorn

from taskhub.main import app


def main() -> None:
    uvicorn.run("taskhub.main:app", host="0.0.0.0", port=8000, reload=True)


__all__ = ["app", "main"]
