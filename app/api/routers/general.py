from fastapi.routing import APIRouter
from starlette.responses import JSONResponse

router = APIRouter()

@router.get('/health')
async def health():
    return JSONResponse({"status": "ok"})

@router.get("/readyz")
def readiness_check():
    return {"status": "ready"}