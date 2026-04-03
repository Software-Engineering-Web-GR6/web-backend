from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_session, require_admin
from app.schemas.auth import (
    BatchImportResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ImportUsersRequest,
    MessageResponse,
    ResetPasswordRequest,
    TokenResponse,
    UserCreateRequest,
    UserResponse,
    UserRoomAccessGrantRequest,
    UserRoomAccessResponse,
    UserScheduleAssignRequest,
    UserScheduleEntryResponse,
    VerifyResetCodeRequest,
)
from app.services.auth_service import auth_service
from app.services.mail_service import MailDeliveryError

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


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        await auth_service.request_password_reset(db, str(payload.email))
    except (ValueError, MailDeliveryError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    return {"message": "If the account exists, a verification code has been sent to the registered email."}


@router.post("/verify-reset-code", response_model=MessageResponse)
async def verify_reset_code(
    payload: VerifyResetCodeRequest,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        await auth_service.verify_password_reset_code(
            db,
            str(payload.email),
            payload.code,
        )
        return {"message": "Verification code is valid"}
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        await auth_service.reset_password_with_code(
            db,
            str(payload.email),
            payload.code,
            payload.new_password,
        )
        return {"message": "Password updated successfully"}
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_admin),
):
    try:
        return await auth_service.create_user(
            db,
            payload.full_name,
            str(payload.email),
            payload.password,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post("/users/import", response_model=BatchImportResponse)
async def import_users(
    payload: ImportUsersRequest,
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_admin),
):
    items = [
        {
            "full_name": item.full_name,
            "email": str(item.email),
            "password": item.password,
        }
        for item in payload.items
    ]
    return await auth_service.import_users(db, items)


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_admin),
):
    return await auth_service.list_users(db)


@router.get("/me", response_model=UserResponse)
async def get_me(
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    user_id_raw = current_user.get("sub")
    if not user_id_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = await auth_service.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.put("/me/password")
async def change_my_password(
    payload: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    user_id_raw = current_user.get("sub")
    if not user_id_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        await auth_service.change_password(
            db,
            user_id=user_id,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
        return {"message": "Password updated successfully"}
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_admin),
):
    try:
        await auth_service.delete_user(db, user_id)
        return {"message": "User deleted successfully"}
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.post("/users/{user_id}/room-access", response_model=list[UserRoomAccessResponse])
async def grant_room_access(
    user_id: int,
    payload: UserRoomAccessGrantRequest,
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_admin),
):
    try:
        return await auth_service.grant_room_shift_access(db, user_id, payload.room_id, payload.shifts, payload.days_of_week)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post("/users/{user_id}/schedule", response_model=list[UserScheduleEntryResponse])
async def assign_user_schedule(
    user_id: int,
    payload: UserScheduleAssignRequest,
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_admin),
):
    try:
        return await auth_service.assign_user_schedule(
            db,
            user_id,
            payload.room_id,
            payload.shifts,
            payload.days_of_week,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get("/users/{user_id}/room-access", response_model=list[UserRoomAccessResponse])
async def list_room_access(
    user_id: int,
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_admin),
):
    return await auth_service.list_room_shift_access(db, user_id)


@router.get("/users/{user_id}/schedule", response_model=list[UserScheduleEntryResponse])
async def list_user_schedule(
    user_id: int,
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_admin),
):
    return await auth_service.list_user_schedule(db, user_id)


@router.get("/rooms/{room_id}/room-access", response_model=list[UserRoomAccessResponse])
async def list_room_occupancy(
    room_id: int,
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_admin),
):
    return await auth_service.list_room_occupancy(db, room_id)


@router.get("/rooms/{room_id}/schedule", response_model=list[UserScheduleEntryResponse])
async def list_room_schedule(
    room_id: int,
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_admin),
):
    return await auth_service.list_room_schedule(db, room_id)


@router.get("/me/room-access", response_model=list[UserRoomAccessResponse])
async def list_my_room_access(
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    user_id_raw = current_user.get("sub")
    if not user_id_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    return await auth_service.list_room_shift_access(db, user_id)


@router.get("/me/schedule", response_model=list[UserScheduleEntryResponse])
async def list_my_schedule(
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    user_id_raw = current_user.get("sub")
    if not user_id_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    return await auth_service.list_user_schedule(db, user_id)


@router.delete("/users/{user_id}/room-access")
async def revoke_room_access(
    user_id: int,
    room_id: int,
    shift_number: int,
    day_of_week: int,
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_admin),
):
    try:
        await auth_service.revoke_room_shift_access(db, user_id, room_id, shift_number, day_of_week)
        return {"message": "Permission revoked successfully"}
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.delete("/users/{user_id}/schedule")
async def remove_user_schedule_entry(
    user_id: int,
    room_id: int,
    shift_number: int,
    day_of_week: int,
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_admin),
):
    try:
        await auth_service.remove_user_schedule_entry(
            db,
            user_id,
            room_id,
            shift_number,
            day_of_week,
        )
        return {"message": "Schedule entry removed successfully"}
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
