from fastapi import APIRouter

from taskhub.api.v1.endpoints import auth, projects, tasks, users, workspaces

api_router = APIRouter()

api_router.include_router(auth.router, tags=["Auth"])
api_router.include_router(users.router, tags=["Users"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["Workspaces"])
api_router.include_router(projects.router, tags=["Projects - Tasks"])
api_router.include_router(tasks.router, tags=["Tasks"])
