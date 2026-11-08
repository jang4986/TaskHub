from fastapi import APIRouter

from taskhub.api.v1.endpoints import projects, tasks

api_router = APIRouter()

api_router.include_router(projects.router, tags=["Projects - Tasks"])
api_router.include_router(tasks.router, tags=["Tasks"])
