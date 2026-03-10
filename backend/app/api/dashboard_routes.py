"""User dashboard API routes — Phase 9.

Endpoints for:
- Projects (CRUD, starring, archiving)
- Conversions (listing, starring, history)
- Presets (CRUD, sharing)
- Usage stats
- Storage quota
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.database import (
    User, Project, Conversion, UserPreset, UsageRecord,
    ProjectStatus, ConversionStatus, PlanTier, PLAN_LIMITS,
)
from app.api.auth_middleware import get_current_active_user
from app.services.cloud_storage import get_cloud_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard (Phase 9)"])


# =============================================================================
# Request / Response Models
# =============================================================================

class CreateProjectRequest(BaseModel):
    name: str = Field(max_length=255, default="Untitled Project")
    description: Optional[str] = None
    tags: List[str] = []

class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    is_starred: Optional[bool] = None
    status: Optional[str] = None

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    status: str
    is_starred: bool
    tags: list
    conversion_count: int = 0
    created_at: str
    updated_at: str

class ConversionResponse(BaseModel):
    id: str
    original_filename: str
    original_format: Optional[str]
    original_size_bytes: Optional[int]
    output_size_bytes: Optional[int]
    status: str
    engine_used: Optional[str]
    quality_mode: Optional[str]
    processing_route: Optional[str]
    processing_time_ms: Optional[int]
    is_starred: bool
    input_url: Optional[str]
    output_url: Optional[str]
    project_id: Optional[str]
    created_at: str
    completed_at: Optional[str]

class CreatePresetRequest(BaseModel):
    name: str = Field(max_length=255)
    description: Optional[str] = None
    config: dict
    is_public: bool = False

class PresetResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    config: dict
    is_public: bool
    is_default: bool
    use_count: int
    created_at: str

class UsageStatsResponse(BaseModel):
    conversions_this_month: int
    conversions_limit: int
    storage_used_bytes: int
    storage_limit_bytes: int
    api_calls_today: int
    api_calls_limit: int
    plan: str
    plan_limits: dict


# =============================================================================
# Projects
# =============================================================================

@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(
    status: Optional[str] = Query(None, description="Filter by status"),
    starred: Optional[bool] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's projects."""
    query = select(Project).where(Project.owner_id == user.id)

    if status:
        query = query.where(Project.status == ProjectStatus(status))
    else:
        query = query.where(Project.status != ProjectStatus.DELETED)
    
    if starred is not None:
        query = query.where(Project.is_starred == starred)

    query = query.order_by(desc(Project.updated_at)).limit(limit).offset(offset)

    result = await db.execute(query)
    projects = result.scalars().all()

    responses = []
    for p in projects:
        # Count conversions
        count_result = await db.execute(
            select(func.count(Conversion.id)).where(Conversion.project_id == p.id)
        )
        conv_count = count_result.scalar() or 0

        responses.append(ProjectResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            status=p.status.value if p.status else "active",
            is_starred=p.is_starred,
            tags=p.tags or [],
            conversion_count=conv_count,
            created_at=p.created_at.isoformat() if p.created_at else "",
            updated_at=p.updated_at.isoformat() if p.updated_at else "",
        ))

    return responses


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(
    request: CreateProjectRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new project."""
    project = Project(
        owner_id=user.id,
        name=request.name,
        description=request.description,
        tags=request.tags,
    )
    db.add(project)
    await db.flush()

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status="active",
        is_starred=False,
        tags=project.tags or [],
        conversion_count=0,
        created_at=project.created_at.isoformat() if project.created_at else "",
        updated_at=project.updated_at.isoformat() if project.updated_at else "",
    )


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    request: UpdateProjectRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a project."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    if request.name is not None:
        project.name = request.name
    if request.description is not None:
        project.description = request.description
    if request.tags is not None:
        project.tags = request.tags
    if request.is_starred is not None:
        project.is_starred = request.is_starred
    if request.status is not None:
        project.status = ProjectStatus(request.status)

    await db.flush()

    count_result = await db.execute(
        select(func.count(Conversion.id)).where(Conversion.project_id == project.id)
    )

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status.value if project.status else "active",
        is_starred=project.is_starred,
        tags=project.tags or [],
        conversion_count=count_result.scalar() or 0,
        created_at=project.created_at.isoformat() if project.created_at else "",
        updated_at=project.updated_at.isoformat() if project.updated_at else "",
    )


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a project."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    project.status = ProjectStatus.DELETED
    await db.flush()

    return {"message": "Project deleted", "id": project_id}


# =============================================================================
# Conversions
# =============================================================================

@router.get("/conversions", response_model=list[ConversionResponse])
async def list_conversions(
    project_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    starred: Optional[bool] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's conversions with optional filtering."""
    query = select(Conversion).where(Conversion.user_id == user.id)

    if project_id:
        query = query.where(Conversion.project_id == project_id)
    if status:
        query = query.where(Conversion.status == ConversionStatus(status))
    if starred is not None:
        query = query.where(Conversion.is_starred == starred)

    query = query.order_by(desc(Conversion.created_at)).limit(limit).offset(offset)

    result = await db.execute(query)
    conversions = result.scalars().all()

    storage = get_cloud_storage()

    return [
        ConversionResponse(
            id=c.id,
            original_filename=c.original_filename,
            original_format=c.original_format,
            original_size_bytes=c.original_size_bytes,
            output_size_bytes=c.output_size_bytes,
            status=c.status.value if c.status else "pending",
            engine_used=c.engine_used,
            quality_mode=c.quality_mode,
            processing_route=c.processing_route,
            processing_time_ms=c.processing_time_ms,
            is_starred=c.is_starred,
            input_url=storage.get_url(c.input_storage_key) if c.input_storage_key else None,
            output_url=storage.get_url(c.output_storage_key) if c.output_storage_key else None,
            project_id=c.project_id,
            created_at=c.created_at.isoformat() if c.created_at else "",
            completed_at=c.completed_at.isoformat() if c.completed_at else None,
        )
        for c in conversions
    ]


@router.patch("/conversions/{conversion_id}/star")
async def toggle_star_conversion(
    conversion_id: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle star on a conversion."""
    result = await db.execute(
        select(Conversion).where(Conversion.id == conversion_id, Conversion.user_id == user.id)
    )
    conversion = result.scalar_one_or_none()
    if not conversion:
        raise HTTPException(404, "Conversion not found")

    conversion.is_starred = not conversion.is_starred
    await db.flush()

    return {"id": conversion_id, "is_starred": conversion.is_starred}


# =============================================================================
# Presets
# =============================================================================

@router.get("/presets", response_model=list[PresetResponse])
async def list_presets(
    include_public: bool = Query(False),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's presets (and optionally public presets)."""
    if include_public:
        query = select(UserPreset).where(
            (UserPreset.user_id == user.id) | (UserPreset.is_public == True)
        )
    else:
        query = select(UserPreset).where(UserPreset.user_id == user.id)

    query = query.order_by(desc(UserPreset.use_count))
    result = await db.execute(query)
    presets = result.scalars().all()

    return [
        PresetResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            config=p.config or {},
            is_public=p.is_public,
            is_default=p.is_default,
            use_count=p.use_count or 0,
            created_at=p.created_at.isoformat() if p.created_at else "",
        )
        for p in presets
    ]


@router.post("/presets", response_model=PresetResponse, status_code=201)
async def create_preset(
    request: CreatePresetRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversion preset."""
    preset = UserPreset(
        user_id=user.id,
        name=request.name,
        description=request.description,
        config=request.config,
        is_public=request.is_public,
    )
    db.add(preset)
    await db.flush()

    return PresetResponse(
        id=preset.id,
        name=preset.name,
        description=preset.description,
        config=preset.config or {},
        is_public=preset.is_public,
        is_default=False,
        use_count=0,
        created_at=preset.created_at.isoformat() if preset.created_at else "",
    )


@router.delete("/presets/{preset_id}")
async def delete_preset(
    preset_id: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a preset."""
    result = await db.execute(
        select(UserPreset).where(UserPreset.id == preset_id, UserPreset.user_id == user.id)
    )
    preset = result.scalar_one_or_none()
    if not preset:
        raise HTTPException(404, "Preset not found")

    await db.delete(preset)
    await db.flush()

    return {"message": "Preset deleted", "id": preset_id}


# =============================================================================
# Usage Stats
# =============================================================================

@router.get("/usage", response_model=UsageStatsResponse)
async def get_usage_stats(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current usage statistics and plan limits."""
    plan_limits = PLAN_LIMITS.get(user.plan, PLAN_LIMITS[PlanTier.FREE])

    # Count conversions this month
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    conv_result = await db.execute(
        select(func.count(Conversion.id)).where(
            Conversion.user_id == user.id,
            Conversion.created_at >= month_start,
        )
    )
    conversions_this_month = conv_result.scalar() or 0

    # Storage usage
    storage = get_cloud_storage()
    storage_info = storage.get_user_storage_usage(user.id)

    return UsageStatsResponse(
        conversions_this_month=conversions_this_month,
        conversions_limit=plan_limits.get("conversions_per_month", 25),
        storage_used_bytes=storage_info.get("total_bytes", 0),
        storage_limit_bytes=plan_limits.get("storage_mb", 500) * 1024 * 1024,
        api_calls_today=0,  # TODO: implement API call counting
        api_calls_limit=plan_limits.get("api_calls_per_day", 100),
        plan=user.plan.value if user.plan else "free",
        plan_limits=plan_limits,
    )
