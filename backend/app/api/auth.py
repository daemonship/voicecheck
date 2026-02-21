"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, constr

from ..services.auth import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: EmailStr
    password: constr(min_length=8, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    user: dict
    token: str


@router.post("/signup", response_model=AuthResponse, status_code=201)
async def signup(request: SignupRequest):
    """Sign up a new user."""
    auth_service = AuthService()
    try:
        result = await auth_service.signup(request.email, request.password)
        return AuthResponse(**result)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Log in an existing user."""
    auth_service = AuthService()
    try:
        result = await auth_service.login(request.email, request.password)
        return AuthResponse(**result)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/logout")
async def logout(token: str = Depends(lambda: None)):  # TODO: implement token extraction from header
    """Log out current user."""
    if token:
        auth_service = AuthService()
        await auth_service.logout(token)
    return {"message": "Logged out"}