from pydantic import BaseModel, Field


class CredentialsIn(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    account_number: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class CredentialsStoreResponse(BaseModel):
    status: str
