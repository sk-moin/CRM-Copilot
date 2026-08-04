from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    subdomain: str
    org_name: str