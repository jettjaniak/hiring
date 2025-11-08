"""
Authentication API routes
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from sqlmodel import Session, select
from pydantic import BaseModel

from ...models import User
from ...dependencies import get_session, get_current_user
from ...auth import hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


# Request/Response models
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    username: str
    email: str
    full_name: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


@router.post("/register", response_model=UserResponse, status_code=201)
def register(
    request: RegisterRequest,
    session: Session = Depends(get_session)
):
    """
    Register a new user account.

    Args:
        request: Registration data including username, email, password, and full_name
        session: Database session

    Returns:
        The created user (without password)

    Raises:
        HTTPException: 400 if username or email already exists
    """
    # Check if username already exists
    existing_user = session.get(User, request.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Check if email already exists
    existing_email = session.exec(
        select(User).where(User.email == request.email)
    ).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already exists")

    # Create new user
    user = User(
        username=request.username,
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    return user


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session)
):
    """
    Login with username and password.

    Args:
        request: FastAPI request object (to access session)
        username: Username
        password: Password
        session: Database session

    Returns:
        Success message with user info

    Raises:
        HTTPException: 401 if credentials are invalid
    """
    # Get user by username
    user = session.get(User, username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Verify password
    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Set session
    request.session["user_id"] = user.username

    return {
        "message": "Login successful",
        "user": {
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name
        }
    }


@router.post("/logout")
def logout(request: Request):
    """
    Logout current user by clearing session.

    Args:
        request: FastAPI request object (to access session)

    Returns:
        Success message
    """
    request.session.clear()
    return {"message": "Logout successful"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get current authenticated user information.

    Args:
        current_user: Current authenticated user from session

    Returns:
        Current user information

    Raises:
        HTTPException: 401 if not authenticated
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return current_user
