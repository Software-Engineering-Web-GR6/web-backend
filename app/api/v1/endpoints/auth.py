from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.schemas.auth import TokenResponse
from app.services.auth_service import auth_service

router = APIRouter()   # KHÔNG để prefix="/auth"


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db_session),
):
    await auth_service.seed_admin_if_empty(db)
    try:
        token = await auth_service.login(
            db,
            form_data.username,   # username ở Swagger chính là email
            form_data.password,
        )
        return {"access_token": token, "token_type": "bearer"}
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )