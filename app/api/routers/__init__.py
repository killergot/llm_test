from fastapi import APIRouter

from app.api.routers.v1 import router as v1_router
from app.api.routers.admin import router as admin_router
from app.api.routers.general import router as detector_router

api_router = APIRouter()
api_router.include_router(v1_router, tags=["v1"])
api_router.include_router(admin_router, tags=["admin"])
api_router.include_router(detector_router, tags=["detector"])