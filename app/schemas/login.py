from typing import Optional

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    message: str


class RegisterResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    message: str


class UnregisterResponse(BaseModel):
    message: str
    deletion_scheduled_at_ms: int
    deletion_at_ms: int


class UserMeResponse(BaseModel):
    user_id: str
    email: Optional[str] = None


class NextRunInfo(BaseModel):
    seconds_until_next_run: Optional[float] = None
    next_run_timestamp_ms: Optional[int] = None

    model_config = {"extra": "allow"}


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetResponse(BaseModel):
    message: str


class JobStatusResponse(BaseModel):
    user_id: str
    has_scheduled_job: bool
    next_run: Optional[NextRunInfo] = None
    deletion_pending: Optional[bool] = None
