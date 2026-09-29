from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    """
    Schema for user registration.
    """
    name: str = Field(..., min_length=2, max_length=100, description="Full name of user")
    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(..., min_length=6, max_length=128, description="User password (min 6 characters)")
    role: Literal["admin", "analyst"] = Field("analyst", description="User role: 'admin' or 'analyst'")


class UserLogin(BaseModel):
    """
    Schema for user login credentials.
    """
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")


class UserResponse(BaseModel):
    """
    Public user schema. NEVER exposes password_hash.
    """
    id: int = Field(..., description="Unique user ID")
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    role: str = Field(..., description="Assigned role ('admin' or 'analyst')")
    created_at: datetime = Field(..., description="Registration timestamp")

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """
    Schema returned upon successful authentication.
    """
    access_token: str = Field(..., description="Signed JWT Bearer token")
    token_type: str = Field("bearer", description="Token type")
    user: UserResponse = Field(..., description="Authenticated user metadata")
