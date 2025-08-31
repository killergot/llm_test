from fastapi.routing import APIRouter
from app.api.routers.v1.sse import router as sse_router

router = APIRouter(prefix="/v1")

router.include_router(sse_router, prefix="/chat")