from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    message: str

class UserInfo(BaseModel):
    access_token: str
    user_name: str = "Anonym"