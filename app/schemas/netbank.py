from pydantic import BaseModel


class CredentialsIn(BaseModel):
    username: str
    account_number: str
    password: str
