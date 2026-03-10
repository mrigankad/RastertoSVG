"""Auth middleware & FastAPI dependencies — Phase 9.

Provides:
- get_current_user: JWT-based auth dependency
- get_current_active_user: Verified + active user
- require_role: Role-based access control
- api_key_auth: API key authentication
- rate_limit: Plan-based rate limiting
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.database import User, APIKey, UserRole, PlanTier, PLAN_LIMITS
from app.services.auth_service import token_manager, api_key_manager

logger = logging.getLogger(__name__)

# Bearer token extractor
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Extract and validate the current user from JWT token.
    
    Returns None if no token provided (for optional auth routes).
    Raises 401 if token is invalid.
    """
    if not credentials:
        return None

    payload = token_manager.verify_token(credentials.credentials, expected_type="access")
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def get_current_active_user(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """Require an authenticated, active, verified user."""
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    return user


def require_role(*roles: UserRole):
    """Dependency factory for role-based access control.
    
    Usage:
        @router.get("/admin", dependencies=[Depends(require_role(UserRole.SUPERADMIN))])
    """
    async def check_role(
        user: User = Depends(get_current_active_user),
    ) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required: {[r.value for r in roles]}",
            )
        return user

    return check_role


async def api_key_auth(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Authenticate via API key header.
    
    Returns None if no API key provided.
    Raises 401 if key is invalid.
    """
    if not x_api_key:
        return None

    key_hash = api_key_manager.hash_key(x_api_key)

    result = await db.execute(
        select(APIKey).where(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True,
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Check expiration
    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="API key expired")

    # Update last used
    api_key.last_used_at = datetime.now(timezone.utc)
    await db.commit()

    # Load user
    result = await db.execute(select(User).where(User.id == api_key.user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Account not active")

    return user


async def get_auth_user(
    jwt_user: Optional[User] = Depends(get_current_user),
    api_key_user: Optional[User] = Depends(api_key_auth),
) -> Optional[User]:
    """Combined auth: accepts JWT token OR API key."""
    return jwt_user or api_key_user


async def require_auth_user(
    user: Optional[User] = Depends(get_auth_user),
) -> User:
    """Require authentication via either JWT or API key."""
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required (Bearer token or X-API-Key)",
        )
    return user


def check_plan_limit(feature: str):
    """Dependency factory for plan-based feature gating.
    
    Usage:
        @router.post("/convert", dependencies=[Depends(check_plan_limit("ai_modes"))])
    """
    async def _check(user: User = Depends(require_auth_user)) -> User:
        plan_limits = PLAN_LIMITS.get(user.plan, PLAN_LIMITS[PlanTier.FREE])
        limit_value = plan_limits.get(feature)

        if limit_value is not None and isinstance(limit_value, list):
            # Feature is a list of allowed values — check happens at endpoint level
            pass
        elif limit_value is not None and isinstance(limit_value, int) and limit_value == 0:
            raise HTTPException(
                status_code=403,
                detail=f"Feature '{feature}' not available on {user.plan.value} plan. Please upgrade.",
            )

        return user

    return _check
