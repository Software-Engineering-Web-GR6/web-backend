from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import (
    get_accessible_room_ids,
    get_current_user,
    get_db_session,
    require_alert_access,
)
from app.schemas.alert import AlertResponse
from app.services.alert_service import alert_service

router = APIRouter()


@router.get("/", response_model=list[AlertResponse])
async def list_alerts(
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") == "admin":
        return await alert_service.list_all(db)

    room_ids = await get_accessible_room_ids(db, current_user)
    return await alert_service.list_all(db, room_ids=room_ids)


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_alert_access),
):
    try:
        return await alert_service.resolve(db, alert_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
