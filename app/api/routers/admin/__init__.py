from fastapi.routing import APIRouter

from app.api.routers.admin.policies import router as policy_router

router = APIRouter(prefix="/admin")

router.include_router(policy_router, tags=["policies"])