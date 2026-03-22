from typing import Optional

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    message: str


class UserMeResponse(BaseModel):
    user_id: str


class NextRunInfo(BaseModel):
    seconds_until_next_run: Optional[float] = None
    next_run_timestamp_ms: Optional[int] = None

    model_config = {"extra": "allow"}
