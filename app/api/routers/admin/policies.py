from fastapi import APIRouter

from app.utils.policy import engine, PolicyViolation, revision

router = APIRouter(prefix="/policies")


@router.post("/reload-policies/")
async def reload_policies():
    engine.refresh()
    print(engine.list_rules())
    global revision
    revision += 1
    return {"status": "ok", "message": "Policies reloaded"}