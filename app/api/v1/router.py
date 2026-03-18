from fastapi import APIRouter

from app.api.v1 import auth, backlog, comments, epics, issues, projects, sprints, users

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
v1_router.include_router(users.router, prefix="/users", tags=["Users"])
v1_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
v1_router.include_router(epics.router, prefix="/projects", tags=["Epics"])
v1_router.include_router(sprints.router, prefix="/projects", tags=["Sprints"])
v1_router.include_router(issues.router, prefix="/projects", tags=["Issues"])
v1_router.include_router(backlog.router, prefix="/projects", tags=["Backlog"])
v1_router.include_router(comments.router, prefix="/projects", tags=["Comments"])
