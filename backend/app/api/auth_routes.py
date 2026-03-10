"""Auth & User API routes — Phase 9.

Endpoints:
- POST /auth/register       — Email+password registration
- POST /auth/login          — Email+password login
- POST /auth/refresh        — Refresh access token
- GET  /auth/oauth/{provider}/url  — Get OAuth login URL
- POST /auth/oauth/{provider}      — OAuth code exchange + login
- POST /auth/verify-email   — Verify email
- POST /auth/forgot-password — Request password reset
- POST /auth/reset-password  — Reset password
- GET  /auth/me              — Get current user profile
- PATCH /auth/me             — Update profile
- GET  /users/{id}/api-keys  — List user's API keys
- POST /users/{id}/api-keys  — Create API key
- DELETE /users/{id}/api-keys/{key_id} — Revoke API key
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.database import (
    User,
    OAuthAccount,
    APIKey,
    UserRole,
    PlanTier,
    OAuthProvider,
    PLAN_LIMITS,
)
from app.services.auth_service import (
    password_hasher,
    token_manager,
    api_key_manager,
    oauth_helper,
    generate_verification_token,
    generate_reset_token,
)
from app.api.auth_middleware import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication (Phase 9)"])


# =============================================================================
# Request / Response Models
# =============================================================================


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: Optional[str] = None
    username: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class OAuthCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: Optional[dict] = None


class UserResponse(BaseModel):
    id: str
    email: str
    username: Optional[str]
    display_name: Optional[str]
    avatar_url: Optional[str]
    role: str
    plan: str
    is_verified: bool
    created_at: str
    plan_limits: dict


class CreateAPIKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    scopes: List[str] = ["convert", "upload"]
    expires_in_days: Optional[int] = None


class APIKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    scopes: list
    is_active: bool
    last_used_at: Optional[str]
    expires_at: Optional[str]
    created_at: str
    key: Optional[str] = None  # Only included on creation


# =============================================================================
# Helper for building user response
# =============================================================================


def _user_to_response(user: User) -> UserResponse:
    plan_limits = PLAN_LIMITS.get(user.plan, PLAN_LIMITS[PlanTier.FREE])
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        role=user.role.value if user.role else "user",
        plan=user.plan.value if user.plan else "free",
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat() if user.created_at else "",
        plan_limits=plan_limits,
    )


def _build_token_response(user: User) -> TokenResponse:
    access_token = token_manager.create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role.value if user.role else "user",
    )
    refresh_token = token_manager.create_refresh_token(user_id=user.id)
    user_resp = _user_to_response(user)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_resp.model_dump(),
    )


# =============================================================================
# Registration & Login
# =============================================================================


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user with email and password."""
    # Check existing
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(400, "Email already registered")

    if request.username:
        result = await db.execute(select(User).where(User.username == request.username))
        if result.scalar_one_or_none():
            raise HTTPException(400, "Username already taken")

    # Create user
    user = User(
        email=request.email,
        username=request.username,
        display_name=request.display_name or request.email.split("@")[0],
        hashed_password=password_hasher.hash_password(request.password),
        verification_token=generate_verification_token(),
        role=UserRole.USER,
        plan=PlanTier.FREE,
    )
    db.add(user)
    await db.flush()  # Get the ID

    logger.info(f"User registered: {user.email} ({user.id})")

    return _build_token_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with email and password."""
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(401, "Invalid email or password")

    if not password_hasher.verify_password(request.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")

    if not user.is_active:
        raise HTTPException(403, "Account deactivated")

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    logger.info(f"User logged in: {user.email}")

    return _build_token_response(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Refresh an access token using a refresh token."""
    payload = token_manager.verify_token(request.refresh_token, expected_type="refresh")
    if not payload:
        raise HTTPException(401, "Invalid or expired refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")

    return _build_token_response(user)


# =============================================================================
# OAuth
# =============================================================================


@router.get("/oauth/{provider}/url")
async def get_oauth_url(provider: str):
    """Get the OAuth authorization URL."""
    url = oauth_helper.get_oauth_url(provider)
    if not url:
        raise HTTPException(400, f"Unsupported provider: {provider}")
    return {"url": url, "provider": provider}


@router.post("/oauth/{provider}", response_model=TokenResponse)
async def oauth_callback(
    provider: str,
    request: OAuthCallbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """Exchange OAuth code for user session."""
    # Exchange code for user info
    exchange_fn = {
        "google": oauth_helper.exchange_google_code,
        "github": oauth_helper.exchange_github_code,
        "microsoft": oauth_helper.exchange_microsoft_code,
    }.get(provider)

    if not exchange_fn:
        raise HTTPException(400, f"Unsupported provider: {provider}")

    user_info = await exchange_fn(request.code)
    if not user_info:
        raise HTTPException(400, "OAuth authentication failed")

    email = user_info.get("email")
    if not email:
        raise HTTPException(400, "Email not provided by OAuth provider")

    provider_enum = OAuthProvider(provider)

    # Check if OAuth account already linked
    result = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.provider == provider_enum,
            OAuthAccount.provider_user_id == user_info["provider_user_id"],
        )
    )
    oauth_account = result.scalar_one_or_none()

    if oauth_account:
        # Existing OAuth link → load user
        result = await db.execute(select(User).where(User.id == oauth_account.user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(500, "Linked user not found")
    else:
        # Check if email matches existing user
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            # Create new user
            user = User(
                email=email,
                display_name=user_info.get("name", email.split("@")[0]),
                avatar_url=user_info.get("avatar"),
                is_verified=True,
                role=UserRole.USER,
                plan=PlanTier.FREE,
            )
            db.add(user)
            await db.flush()

        # Link OAuth account
        oauth_link = OAuthAccount(
            user_id=user.id,
            provider=provider_enum,
            provider_user_id=user_info["provider_user_id"],
            provider_email=email,
            access_token=user_info.get("access_token"),
            refresh_token=user_info.get("refresh_token"),
        )
        db.add(oauth_link)

    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    logger.info(f"OAuth login: {user.email} via {provider}")

    return _build_token_response(user)


# =============================================================================
# Email Verification & Password Reset
# =============================================================================


@router.post("/verify-email")
async def verify_email(request: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    """Verify user email with token."""
    result = await db.execute(select(User).where(User.verification_token == request.token))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(400, "Invalid verification token")

    user.is_verified = True
    user.verification_token = None
    await db.flush()

    return {"message": "Email verified successfully"}


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Request a password reset email."""
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    if user and user.hashed_password:
        user.reset_token = generate_reset_token()
        from datetime import timedelta

        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=2)
        await db.flush()
        # TODO: Send email with reset link
        logger.info(f"Password reset requested for: {user.email}")

    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Reset password using token."""
    result = await db.execute(select(User).where(User.reset_token == request.token))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(400, "Invalid reset token")

    if user.reset_token_expires and user.reset_token_expires < datetime.now(timezone.utc):
        raise HTTPException(400, "Reset token expired")

    user.hashed_password = password_hasher.hash_password(request.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    await db.flush()

    return {"message": "Password reset successfully"}


# =============================================================================
# Profile
# =============================================================================


@router.get("/me", response_model=UserResponse)
async def get_profile(user: User = Depends(get_current_active_user)):
    """Get current user profile."""
    return _user_to_response(user)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    request: UpdateProfileRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user profile."""
    if request.display_name is not None:
        user.display_name = request.display_name
    if request.username is not None:
        # Check uniqueness
        result = await db.execute(
            select(User).where(User.username == request.username, User.id != user.id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(400, "Username already taken")
        user.username = request.username
    if request.avatar_url is not None:
        user.avatar_url = request.avatar_url
    if request.preferences is not None:
        user.preferences = request.preferences

    await db.flush()
    return _user_to_response(user)


# =============================================================================
# API Keys
# =============================================================================


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all API keys for the current user."""
    result = await db.execute(
        select(APIKey).where(APIKey.user_id == user.id).order_by(APIKey.created_at.desc())
    )
    keys = result.scalars().all()

    return [
        APIKeyResponse(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            scopes=k.scopes or [],
            is_active=k.is_active,
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
            expires_at=k.expires_at.isoformat() if k.expires_at else None,
            created_at=k.created_at.isoformat() if k.created_at else "",
        )
        for k in keys
    ]


@router.post("/api-keys", response_model=APIKeyResponse, status_code=201)
async def create_api_key(
    request: CreateAPIKeyRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new API key. The full key is only returned once."""
    full_key, key_prefix, key_hash = api_key_manager.generate_key()

    expires_at = None
    if request.expires_in_days:
        from datetime import timedelta

        expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_in_days)

    api_key = APIKey(
        user_id=user.id,
        name=request.name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        scopes=request.scopes,
        expires_at=expires_at,
    )
    db.add(api_key)
    await db.flush()

    logger.info(f"API key created: {key_prefix}... for user {user.email}")

    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=key_prefix,
        scopes=api_key.scopes or [],
        is_active=True,
        last_used_at=None,
        expires_at=expires_at.isoformat() if expires_at else None,
        created_at=api_key.created_at.isoformat() if api_key.created_at else "",
        key=full_key,  # Only returned on creation
    )


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an API key."""
    result = await db.execute(select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user.id))
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(404, "API key not found")

    api_key.is_active = False
    await db.flush()

    return {"message": "API key revoked", "key_id": key_id}
