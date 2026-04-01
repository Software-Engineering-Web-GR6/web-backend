from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=6, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyResetCodeRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=12)


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=12)
    new_password: str = Field(min_length=6, max_length=128)


class MessageResponse(BaseModel):
    message: str


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserRoomAccessGrantRequest(BaseModel):
    room_id: int = Field(gt=0)
    shifts: list[int] = Field(min_length=1, max_length=6)
    days_of_week: list[int] = Field(min_length=1, max_length=7)


class UserRoomAccessResponse(BaseModel):
    id: int
    user_id: int
    room_id: int
    shift_number: int
    day_of_week: int
    created_at: datetime

    model_config = {"from_attributes": True}


class UserScheduleAssignRequest(UserRoomAccessGrantRequest):
    pass


class UserScheduleEntryResponse(UserRoomAccessResponse):
    pass
