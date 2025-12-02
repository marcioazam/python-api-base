"""Authentication routes for login, register, token management.

**Feature: core-rbac-system**
**Part of: Core API (permanent)**
"""

from datetime import datetime, timedelta, UTC
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, Field, field_validator
import re

from application.common.dto import ApiResponse
from core.shared.utils.password import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


# === DTOs ===


class LoginRequest(BaseModel):
    """Login request."""

    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", v):
            raise ValueError("Invalid email format")
        return v.lower()


class RegisterRequest(BaseModel):
    """User registration request."""

    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=100)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", v):
            raise ValueError("Invalid email format")
        return v.lower()


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str | None = None


class UserResponse(BaseModel):
    """User response."""

    id: str
    email: str
    display_name: str | None
    is_active: bool
    roles: list[str]
    created_at: datetime


# === Mock Storage (replace with DB in production) ===

_users: dict[str, dict] = {}
_user_roles: dict[str, list[str]] = {}


def _create_token(user_id: str, expires_in: int = 3600) -> str:
    """Create a mock JWT token."""
    import base64
    import json

    payload = {
        "sub": user_id,
        "iat": datetime.now(UTC).timestamp(),
        "exp": (datetime.now(UTC) + timedelta(seconds=expires_in)).timestamp(),
    }
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


# === Routes ===


@router.post(
    "/register",
    response_model=ApiResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
)
async def register(data: RegisterRequest) -> ApiResponse[UserResponse]:
    """Register a new user account."""
    # Check if email exists
    if any(u["email"] == data.email for u in _users.values()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user_id = str(uuid4())
    now = datetime.now(UTC)

    user = {
        "id": user_id,
        "email": data.email,
        "password_hash": hash_password(data.password),
        "display_name": data.display_name,
        "is_active": True,
        "is_verified": False,
        "created_at": now,
        "updated_at": now,
    }
    _users[user_id] = user
    _user_roles[user_id] = ["user"]  # Default role

    return ApiResponse(
        data=UserResponse(
            id=user_id,
            email=user["email"],
            display_name=user["display_name"],
            is_active=user["is_active"],
            roles=_user_roles[user_id],
            created_at=user["created_at"],
        ),
        status_code=201,
    )


@router.post(
    "/login",
    response_model=ApiResponse[TokenResponse],
    summary="User login",
)
async def login(data: LoginRequest) -> ApiResponse[TokenResponse]:
    """Authenticate user and return tokens."""
    # Find user by email
    user = next((u for u in _users.values() if u["email"] == data.email), None)

    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    expires_in = 3600  # 1 hour
    access_token = _create_token(user["id"], expires_in)
    refresh_token = _create_token(user["id"], 86400 * 7)  # 7 days

    return ApiResponse(
        data=TokenResponse(
            access_token=access_token,
            expires_in=expires_in,
            refresh_token=refresh_token,
        )
    )


@router.get(
    "/me",
    response_model=ApiResponse[UserResponse],
    summary="Get current user",
)
async def get_current_user(
    authorization: str = Header(..., alias="Authorization"),
) -> ApiResponse[UserResponse]:
    """Get current authenticated user."""
    import base64
    import json

    try:
        # Extract token from Bearer scheme
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")

        token = authorization[7:]
        payload = json.loads(base64.urlsafe_b64decode(token))
        user_id = payload["sub"]

        # Check expiration
        if payload["exp"] < datetime.now(UTC).timestamp():
            raise HTTPException(status_code=401, detail="Token expired")

        user = _users.get(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return ApiResponse(
            data=UserResponse(
                id=user["id"],
                email=user["email"],
                display_name=user["display_name"],
                is_active=user["is_active"],
                roles=_user_roles.get(user_id, []),
                created_at=user["created_at"],
            )
        )

    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout user",
)
async def logout(
    authorization: str = Header(..., alias="Authorization"),
) -> None:
    """Logout user (invalidate token)."""
    # In a real implementation, add token to blacklist
    pass
