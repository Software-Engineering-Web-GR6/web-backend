from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db_session, get_current_user
from app.schemas.alert import AlertResponse
from app.services.alert_service import alert_service

router = APIRouter()


@router.get("/", response_model=list[AlertResponse])
async def list_alerts(db: AsyncSession = Depends(get_db_session), _: dict = Depends(get_current_user)):
    return await alert_service.list_all(db)


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(alert_id: int, db: AsyncSession = Depends(get_db_session), _: dict = Depends(get_current_user)):
    try:
        return await alert_service.resolve(db, alert_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
