from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter
from pydantic import BaseModel

from app.utils.policy import engine, PolicyViolation

router = APIRouter(prefix="/policies")


class RuleOut(BaseModel):
    id: str
    enabled: bool
    stage: str
    action: str
    priority: int
    message: str
    pattern: str
    redact_with: Optional[str] = None

class EngineOut(BaseModel):
    revision: int
    loaded_at: datetime
    rules: List[RuleOut]


@router.post("/reload")
async def reload_policies():
    engine.refresh()
    return {"status": "ok", "message": "Policies reloaded"}

@router.get("/effective")
async def effective_policies():
    rules_list = engine.list_rules()
    rules_list = [rule for rule in rules_list if rule["enabled"]]

    return EngineOut(
        revision=engine.revision,
        loaded_at=engine.loaded_at,
        rules=rules_list
    )
