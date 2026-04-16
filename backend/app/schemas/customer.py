from pydantic import BaseModel, EmailStr

class CustomerRegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class CustomerLoginRequest(BaseModel):
    email: EmailStr
    password: str

class CustomerResponse(BaseModel):
    id: str
    name: str
    email: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
