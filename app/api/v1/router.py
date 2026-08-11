from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.internal import router as internal_router
from app.api.v1.orgs import router as orgs_router
from app.api.v1.projects import router as projects_router
from app.api.v1.reminders import router as reminders_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.websites import router as websites_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(orgs_router)
api_v1_router.include_router(projects_router)
api_v1_router.include_router(tasks_router)
api_v1_router.include_router(websites_router)
api_v1_router.include_router(reminders_router)
api_v1_router.include_router(internal_router)
