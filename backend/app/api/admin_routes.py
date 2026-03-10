"""Admin Dashboard API routes — Phase 12.

Endpoints:
- GET  /admin/stats              — Platform statistics dashboard
- GET  /admin/users              — List/search users
- PATCH /admin/users/{id}        — Update user (ban, plan override, role)
- GET  /admin/audit-logs         — Query audit logs
- GET  /admin/revenue            — Revenue metrics
- GET  /admin/conversions/stats  — Conversion analytics
- GET  /admin/system/health      — System health & resource usage
- POST /admin/licenses           — Generate license key
- GET  /admin/licenses           — List license keys
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.database import (
    User,
    Team,
    Project,
    Conversion,
    UserRole,
    PlanTier,
    ConversionStatus,
)
from app.models.billing import (
    Subscription,
    Invoice,
    AuditLog,
    LicenseKey,
    SubscriptionStatus,
    AuditAction,
    LicenseType,
    PRICING,
)
from app.api.auth_middleware import require_role
from app.services.billing_service import (
    get_audit_logger,
    get_license_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Dashboard (Phase 12)"])


# =============================================================================
# Response Models
# =============================================================================


class PlatformStatsResponse(BaseModel):
    total_users: int
    active_users_30d: int
    total_teams: int
    total_projects: int
    total_conversions: int
    conversions_today: int
    conversions_this_week: int
    users_by_plan: dict
    conversion_success_rate: float
    avg_conversion_time_ms: float


class UserAdminResponse(BaseModel):
    id: str
    email: str
    username: Optional[str]
    display_name: Optional[str]
    role: str
    plan: str
    is_active: bool
    is_verified: bool
    conversions_count: int = 0
    created_at: str
    last_login_at: Optional[str]


class AuditLogResponse(BaseModel):
    id: str
    user_id: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    description: Optional[str]
    ip_address: Optional[str]
    created_at: str


class RevenueResponse(BaseModel):
    total_mrr_cents: int
    total_arr_cents: int
    active_subscriptions: int
    churned_30d: int
    revenue_by_plan: dict
    total_invoiced_cents: int


class ConversionAnalytics(BaseModel):
    total: int
    completed: int
    failed: int
    success_rate: float
    avg_time_ms: float
    by_engine: dict
    by_route: dict
    by_day: list


class SystemHealthResponse(BaseModel):
    status: str
    uptime_seconds: float
    database: str
    redis: str
    storage: str
    cpu_percent: float
    memory_mb: float


class LicenseResponse(BaseModel):
    id: str
    key_prefix: str
    license_type: str
    organization: Optional[str]
    max_users: int
    is_active: bool
    activations: int
    max_activations: int
    issued_at: str
    expires_at: Optional[str]
    key: Optional[str] = None


# =============================================================================
# Platform Stats
# =============================================================================


@router.get("/stats", response_model=PlatformStatsResponse)
async def get_platform_stats(
    _user: User = Depends(require_role(UserRole.SUPERADMIN, UserRole.ENTERPRISE_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Get platform-wide statistics."""
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    week_ago = now - timedelta(days=7)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # User counts
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    active_30d = (
        await db.execute(select(func.count(User.id)).where(User.last_login_at >= thirty_days_ago))
    ).scalar() or 0

    # Users by plan
    users_by_plan = {}
    for plan in PlanTier:
        count = (
            await db.execute(select(func.count(User.id)).where(User.plan == plan))
        ).scalar() or 0
        users_by_plan[plan.value] = count

    # Other counts
    total_teams = (await db.execute(select(func.count(Team.id)))).scalar() or 0
    total_projects = (await db.execute(select(func.count(Project.id)))).scalar() or 0
    total_conversions = (await db.execute(select(func.count(Conversion.id)))).scalar() or 0

    conversions_today = (
        await db.execute(
            select(func.count(Conversion.id)).where(Conversion.created_at >= today_start)
        )
    ).scalar() or 0

    conversions_week = (
        await db.execute(select(func.count(Conversion.id)).where(Conversion.created_at >= week_ago))
    ).scalar() or 0

    # Success rate
    completed = (
        await db.execute(
            select(func.count(Conversion.id)).where(Conversion.status == ConversionStatus.COMPLETED)
        )
    ).scalar() or 0
    success_rate = (completed / total_conversions * 100) if total_conversions > 0 else 0.0

    # Avg time
    avg_time = (
        await db.execute(
            select(func.avg(Conversion.processing_time_ms)).where(
                Conversion.processing_time_ms.isnot(None)
            )
        )
    ).scalar() or 0.0

    return PlatformStatsResponse(
        total_users=total_users,
        active_users_30d=active_30d,
        total_teams=total_teams,
        total_projects=total_projects,
        total_conversions=total_conversions,
        conversions_today=conversions_today,
        conversions_this_week=conversions_week,
        users_by_plan=users_by_plan,
        conversion_success_rate=round(success_rate, 2),
        avg_conversion_time_ms=round(float(avg_time), 2),
    )


# =============================================================================
# User Management
# =============================================================================


@router.get("/users", response_model=list[UserAdminResponse])
async def list_users(
    query: Optional[str] = Query(None, description="Search by email or username"),
    plan: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    sort_by: str = Query("created_at"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    _user: User = Depends(require_role(UserRole.SUPERADMIN, UserRole.ENTERPRISE_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """List and search users (admin only)."""
    stmt = select(User)

    if query:
        stmt = stmt.where(User.email.ilike(f"%{query}%") | User.username.ilike(f"%{query}%"))
    if plan:
        stmt = stmt.where(User.plan == PlanTier(plan))
    if role:
        stmt = stmt.where(User.role == UserRole(role))
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)

    stmt = stmt.order_by(desc(User.created_at)).limit(limit).offset(offset)

    result = await db.execute(stmt)
    users = result.scalars().all()

    responses = []
    for u in users:
        conv_count = (
            await db.execute(select(func.count(Conversion.id)).where(Conversion.user_id == u.id))
        ).scalar() or 0

        responses.append(
            UserAdminResponse(
                id=u.id,
                email=u.email,
                username=u.username,
                display_name=u.display_name,
                role=u.role.value if u.role else "user",
                plan=u.plan.value if u.plan else "free",
                is_active=u.is_active,
                is_verified=u.is_verified,
                conversions_count=conv_count,
                created_at=u.created_at.isoformat() if u.created_at else "",
                last_login_at=u.last_login_at.isoformat() if u.last_login_at else None,
            )
        )

    return responses


@router.patch("/users/{user_id}")
async def admin_update_user(
    user_id: str,
    is_active: Optional[bool] = None,
    plan: Optional[str] = None,
    role: Optional[str] = None,
    admin: User = Depends(require_role(UserRole.SUPERADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Update user account (ban, plan override, role change)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    audit = get_audit_logger()
    changes = []

    if is_active is not None and user.is_active != is_active:
        user.is_active = is_active
        action = "admin_user_unban" if is_active else "admin_user_ban"
        changes.append(f"active={is_active}")
        await audit.log(
            action=action,
            user_id=admin.id,
            resource_type="user",
            resource_id=user_id,
            description=f"Admin {'unbanned' if is_active else 'banned'} user {user.email}",
            db_session=db,
        )

    if plan:
        try:
            user.plan = PlanTier(plan)
            changes.append(f"plan={plan}")
            await audit.log(
                action="admin_plan_override",
                user_id=admin.id,
                resource_type="user",
                resource_id=user_id,
                description=f"Plan overridden to {plan} for {user.email}",
                db_session=db,
            )
        except ValueError:
            raise HTTPException(400, f"Invalid plan: {plan}")

    if role:
        try:
            user.role = UserRole(role)
            changes.append(f"role={role}")
        except ValueError:
            raise HTTPException(400, f"Invalid role: {role}")

    await db.flush()

    return {
        "message": f"User updated: {', '.join(changes)}",
        "user_id": user_id,
    }


# =============================================================================
# Audit Logs
# =============================================================================


@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def get_audit_logs(
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    days: int = Query(30, le=365),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    _user: User = Depends(require_role(UserRole.SUPERADMIN, UserRole.ENTERPRISE_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Query audit logs (admin only)."""
    stmt = select(AuditLog)

    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if action:
        try:
            stmt = stmt.where(AuditLog.action == AuditAction(action))
        except ValueError:
            raise HTTPException(400, f"Invalid action: {action}")
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = stmt.where(AuditLog.created_at >= cutoff)

    stmt = stmt.order_by(desc(AuditLog.created_at)).limit(limit).offset(offset)

    result = await db.execute(stmt)
    logs = result.scalars().all()

    return [
        AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            action=log.action.value if log.action else "",
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            description=log.description,
            ip_address=log.ip_address,
            created_at=log.created_at.isoformat() if log.created_at else "",
        )
        for log in logs
    ]


# =============================================================================
# Revenue
# =============================================================================


@router.get("/revenue", response_model=RevenueResponse)
async def get_revenue(
    _user: User = Depends(require_role(UserRole.SUPERADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Get revenue metrics."""
    # Active subscriptions and MRR
    result = await db.execute(
        select(Subscription).where(
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
    )
    active_subs = result.scalars().all()

    total_mrr = sum(s.amount_cents or 0 for s in active_subs)

    revenue_by_plan = {}
    for sub in active_subs:
        plan = sub.plan or "unknown"
        revenue_by_plan[plan] = revenue_by_plan.get(plan, 0) + (sub.amount_cents or 0)

    # Churned in 30 days
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    churned = (
        await db.execute(
            select(func.count(Subscription.id)).where(
                Subscription.status == SubscriptionStatus.CANCELED,
                Subscription.canceled_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    # Total invoiced
    total_invoiced = (await db.execute(select(func.sum(Invoice.total_cents)))).scalar() or 0

    return RevenueResponse(
        total_mrr_cents=total_mrr,
        total_arr_cents=total_mrr * 12,
        active_subscriptions=len(active_subs),
        churned_30d=churned,
        revenue_by_plan=revenue_by_plan,
        total_invoiced_cents=total_invoiced,
    )


# =============================================================================
# Conversion Analytics
# =============================================================================


@router.get("/conversions/stats", response_model=ConversionAnalytics)
async def get_conversion_analytics(
    days: int = Query(30, le=365),
    _user: User = Depends(require_role(UserRole.SUPERADMIN, UserRole.ENTERPRISE_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Get conversion analytics."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    total = (
        await db.execute(select(func.count(Conversion.id)).where(Conversion.created_at >= cutoff))
    ).scalar() or 0

    completed = (
        await db.execute(
            select(func.count(Conversion.id)).where(
                Conversion.created_at >= cutoff,
                Conversion.status == ConversionStatus.COMPLETED,
            )
        )
    ).scalar() or 0

    failed = (
        await db.execute(
            select(func.count(Conversion.id)).where(
                Conversion.created_at >= cutoff,
                Conversion.status == ConversionStatus.FAILED,
            )
        )
    ).scalar() or 0

    avg_time = (
        await db.execute(
            select(func.avg(Conversion.processing_time_ms)).where(
                Conversion.created_at >= cutoff,
                Conversion.processing_time_ms.isnot(None),
            )
        )
    ).scalar() or 0.0

    return ConversionAnalytics(
        total=total,
        completed=completed,
        failed=failed,
        success_rate=round((completed / total * 100) if total else 0, 2),
        avg_time_ms=round(float(avg_time), 2),
        by_engine={},  # TODO: aggregate by engine_used
        by_route={},  # TODO: aggregate by processing_route
        by_day=[],  # TODO: daily breakdown
    )


# =============================================================================
# System Health
# =============================================================================


@router.get("/system/health", response_model=SystemHealthResponse)
async def get_system_health(
    _user: User = Depends(require_role(UserRole.SUPERADMIN)),
):
    """Get system health and resource usage."""
    import time as _time

    # Process info
    try:
        import psutil

        cpu = psutil.cpu_percent()
        mem = psutil.Process().memory_info().rss / 1024 / 1024
    except ImportError:
        cpu = 0.0
        mem = 0.0

    # Check database
    db_status = "healthy"
    try:
        from app.database import engine

        async with engine.connect() as conn:
            await conn.execute(select(func.count()).select_from(User))
    except Exception:
        db_status = "unhealthy"

    # Check Redis
    redis_status = "unknown"
    try:
        import redis

        r = redis.from_url("redis://localhost:6379")
        r.ping()
        redis_status = "healthy"
    except Exception:
        redis_status = "unavailable"

    return SystemHealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        uptime_seconds=_time.time(),
        database=db_status,
        redis=redis_status,
        storage="healthy",
        cpu_percent=cpu,
        memory_mb=round(mem, 2),
    )


# =============================================================================
# License Keys
# =============================================================================


@router.post("/licenses", response_model=LicenseResponse, status_code=201)
async def generate_license(
    license_type: str = "self_hosted",
    organization: Optional[str] = None,
    max_users: int = 1,
    max_activations: int = 3,
    expires_in_days: Optional[int] = None,
    admin: User = Depends(require_role(UserRole.SUPERADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new license key for self-hosted deployment."""
    license_service = get_license_service()

    try:
        lt = LicenseType(license_type)
    except ValueError:
        raise HTTPException(400, f"Invalid license type: {license_type}")

    full_key, key_prefix, key_hash = license_service.generate_license_key()

    expires_at = None
    if expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

    license_key = LicenseKey(
        user_id=admin.id,
        license_type=lt,
        key_hash=key_hash,
        key_prefix=key_prefix,
        organization=organization,
        max_users=max_users,
        max_activations=max_activations,
        expires_at=expires_at,
    )
    db.add(license_key)
    await db.flush()

    audit = get_audit_logger()
    await audit.log(
        action="admin_config_change",
        user_id=admin.id,
        resource_type="license",
        resource_id=license_key.id,
        description=f"License generated: {key_prefix}... ({license_type})",
        db_session=db,
    )

    return LicenseResponse(
        id=license_key.id,
        key_prefix=key_prefix,
        license_type=license_type,
        organization=organization,
        max_users=max_users,
        is_active=True,
        activations=0,
        max_activations=max_activations,
        issued_at=license_key.issued_at.isoformat() if license_key.issued_at else "",
        expires_at=expires_at.isoformat() if expires_at else None,
        key=full_key,  # Only returned on creation
    )


@router.get("/licenses", response_model=list[LicenseResponse])
async def list_licenses(
    _user: User = Depends(require_role(UserRole.SUPERADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """List all license keys."""
    result = await db.execute(select(LicenseKey).order_by(desc(LicenseKey.issued_at)))
    keys = result.scalars().all()

    return [
        LicenseResponse(
            id=k.id,
            key_prefix=k.key_prefix,
            license_type=k.license_type.value if k.license_type else "self_hosted",
            organization=k.organization,
            max_users=k.max_users or 1,
            is_active=k.is_active,
            activations=k.activations or 0,
            max_activations=k.max_activations or 3,
            issued_at=k.issued_at.isoformat() if k.issued_at else "",
            expires_at=k.expires_at.isoformat() if k.expires_at else None,
        )
        for k in keys
    ]
