"""Authentication and user management routes."""
from fastapi import APIRouter, HTTPException, Request, Header
from typing import Optional
from .schemas import (
    SignupRequest, SignupResponse,
    LoginRequest, LoginResponse,
    UserInfo
)
from .services.user_service import (
    signup, login, get_user_by_id, verify_token
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=SignupResponse)
async def signup_handler(payload: SignupRequest):
    """Create a new user account."""
    try:
        user = await signup(payload.email, payload.password, payload.name)
        return SignupResponse(**user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")


@router.post("/login", response_model=LoginResponse)
async def login_handler(payload: LoginRequest):
    """Authenticate user and return access token."""
    try:
        result = await login(payload.email, payload.password)
        return LoginResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.get("/me", response_model=UserInfo)
async def get_current_user(authorization: Optional[str] = Header(None)):
    """Get current user info from token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = authorization.split(" ")[1]
    token_data = verify_token(token)
    
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = await get_user_by_id(token_data["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserInfo(
        user_id=user["user_id"],
        email=user["email"],
        name=user["name"],
        role=user["role"]
    )
