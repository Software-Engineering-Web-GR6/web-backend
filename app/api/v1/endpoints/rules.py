from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db_session, require_admin, require_room_access
from app.schemas.automation_rule import RuleCreate, RuleResponse, RuleUpdate
from app.services.rule_service import rule_service

router = APIRouter()


@router.get("/room/{room_id}", response_model=list[RuleResponse])
async def list_rules(room_id: int, db: AsyncSession = Depends(get_db_session), _: dict = Depends(require_room_access)):
    return await rule_service.list_by_room(db, room_id)

@router.post("/", response_model=RuleResponse)
async def create_rule(payload: RuleCreate, db: AsyncSession = Depends(get_db_session), _: dict = Depends(require_admin)):
    try:
        return await rule_service.create(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(rule_id: int, payload: RuleUpdate, db: AsyncSession = Depends(get_db_session), _: dict = Depends(require_admin)):
    try:
        return await rule_service.update(db, rule_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{rule_id}")
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db_session), _: dict = Depends(require_admin)):
    try:
        await rule_service.delete(db, rule_id)
        return {"message": "Rule deleted successfully"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
