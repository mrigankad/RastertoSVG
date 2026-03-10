"""Plugin & Marketplace API routes — Phase 11.

Endpoints:
- GET  /plugins                     — List installed plugins
- POST /plugins/install             — Install a plugin
- POST /plugins/{id}/load           — Load/activate a plugin
- POST /plugins/{id}/unload         — Unload/deactivate a plugin
- POST /plugins/{id}/execute        — Execute a plugin method
- DELETE /plugins/{id}              — Uninstall a plugin
- GET  /plugins/{id}/settings       — Get plugin settings schema

- GET  /marketplace/search          — Search marketplace listings
- GET  /marketplace/featured        — Get featured plugins
- GET  /marketplace/{id}            — Get listing details
- GET  /marketplace/{id}/reviews    — Get listing reviews
- POST /marketplace/{id}/reviews    — Submit a review
- GET  /marketplace/stats           — Marketplace statistics

- GET  /templates                   — List community templates
- GET  /templates/featured          — Featured templates
- GET  /templates/{id}              — Get template details
- POST /templates                   — Create a template
- POST /templates/{id}/use          — Record template usage
"""

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from pydantic import BaseModel, Field

from app.services.plugin_sdk import (
    PluginRegistry,
    PluginType,
    PluginStatus,
    get_plugin_registry,
)
from app.services.marketplace import (
    MarketplaceService,
    MarketplaceListing,
    PluginReview,
    ConversionTemplate,
    TemplateCategory,
    get_marketplace,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Plugins & Marketplace (Phase 11)"])


# =============================================================================
# Request / Response Models
# =============================================================================

class PluginResponse(BaseModel):
    id: str
    name: str
    version: str
    description: str
    author: str
    plugin_type: str
    status: str
    tags: list
    permissions: list
    use_count: int = 0
    avg_execution_ms: float = 0.0
    error: Optional[str] = None

class ExecutePluginRequest(BaseModel):
    method: str = "process"
    params: dict = {}

class MarketplaceListingResponse(BaseModel):
    id: str
    name: str
    version: str
    description: str
    author: str
    plugin_type: str
    tags: list
    downloads: int
    rating: float
    review_count: int
    is_free: bool
    price_usd: float
    icon_url: str = ""
    created_at: str = ""

class ReviewRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    title: str = ""
    body: str = ""
    user_name: str = ""

class ReviewResponse(BaseModel):
    id: str
    rating: int
    title: str
    body: str
    user_name: str
    created_at: str

class TemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    author: str
    category: str
    config: dict
    use_count: int
    rating: float
    is_featured: bool
    tags: list

class CreateTemplateRequest(BaseModel):
    name: str = Field(max_length=255)
    description: str = ""
    category: str = "other"
    config: dict = {}
    tags: List[str] = []

class MarketplaceStatsResponse(BaseModel):
    total_plugins: int
    total_templates: int
    total_downloads: int
    total_reviews: int
    avg_rating: float
    plugins_by_type: dict
    free_plugins: int
    paid_plugins: int


# =============================================================================
# Plugin Endpoints
# =============================================================================

@router.get("/plugins", response_model=list[PluginResponse])
async def list_plugins(
    plugin_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    """List all installed plugins."""
    registry = get_plugin_registry()

    pt = PluginType(plugin_type) if plugin_type else None
    ps = PluginStatus(status) if status else None

    plugins = registry.list_plugins(plugin_type=pt, status=ps)

    return [
        PluginResponse(
            id=p.manifest.id,
            name=p.manifest.name,
            version=p.manifest.version,
            description=p.manifest.description,
            author=p.manifest.author,
            plugin_type=p.manifest.plugin_type.value,
            status=p.status.value,
            tags=p.manifest.tags,
            permissions=p.manifest.permissions,
            use_count=p.use_count,
            avg_execution_ms=p.avg_execution_ms,
            error=p.error,
        )
        for p in plugins
    ]


@router.post("/plugins/install", response_model=PluginResponse, status_code=201)
async def install_plugin(
    manifest: str = Form(..., description="JSON manifest string"),
    entry_file: UploadFile = File(..., description="Main plugin .py file"),
):
    """Install a new plugin from manifest + entry file."""
    registry = get_plugin_registry()

    try:
        manifest_data = json.loads(manifest)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON manifest")

    if not manifest_data.get("name"):
        raise HTTPException(400, "Plugin manifest must include 'name'")

    # Read plugin file
    file_data = await entry_file.read()
    entry_filename = manifest_data.get("entry_point", "main") + ".py"
    plugin_files = {entry_filename: file_data}

    try:
        plugin_id = registry.install_plugin(manifest_data, plugin_files)
    except Exception as e:
        raise HTTPException(500, f"Installation failed: {str(e)}")

    plugin = registry.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(500, "Plugin installed but not found in registry")

    return PluginResponse(
        id=plugin.manifest.id,
        name=plugin.manifest.name,
        version=plugin.manifest.version,
        description=plugin.manifest.description,
        author=plugin.manifest.author,
        plugin_type=plugin.manifest.plugin_type.value,
        status=plugin.status.value,
        tags=plugin.manifest.tags,
        permissions=plugin.manifest.permissions,
    )


@router.post("/plugins/{plugin_id}/load")
async def load_plugin(plugin_id: str):
    """Load and activate a plugin."""
    registry = get_plugin_registry()

    if not registry.get_plugin(plugin_id):
        raise HTTPException(404, "Plugin not found")

    success = registry.load_plugin(plugin_id)
    if not success:
        plugin = registry.get_plugin(plugin_id)
        error = plugin.error if plugin else "Unknown error"
        raise HTTPException(500, f"Failed to load plugin: {error}")

    return {"message": f"Plugin {plugin_id} loaded successfully", "status": "active"}


@router.post("/plugins/{plugin_id}/unload")
async def unload_plugin(plugin_id: str):
    """Unload and deactivate a plugin."""
    registry = get_plugin_registry()

    if not registry.get_plugin(plugin_id):
        raise HTTPException(404, "Plugin not found")

    registry.unload_plugin(plugin_id)
    return {"message": f"Plugin {plugin_id} unloaded", "status": "disabled"}


@router.post("/plugins/{plugin_id}/execute")
async def execute_plugin(plugin_id: str, request: ExecutePluginRequest):
    """Execute a method on a loaded plugin."""
    registry = get_plugin_registry()

    plugin = registry.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(404, "Plugin not found")
    if plugin.status != PluginStatus.ACTIVE:
        raise HTTPException(400, "Plugin is not active. Load it first.")

    try:
        result = registry.execute_plugin(plugin_id, request.method, request.params)
        return {
            "plugin_id": plugin_id,
            "method": request.method,
            "result": result if isinstance(result, (dict, list, str, int, float, bool)) else str(result),
            "use_count": plugin.use_count,
        }
    except Exception as e:
        raise HTTPException(500, f"Plugin execution failed: {str(e)}")


@router.delete("/plugins/{plugin_id}")
async def uninstall_plugin(plugin_id: str):
    """Uninstall a plugin completely."""
    registry = get_plugin_registry()

    if not registry.get_plugin(plugin_id):
        raise HTTPException(404, "Plugin not found")

    registry.uninstall_plugin(plugin_id)
    return {"message": f"Plugin {plugin_id} uninstalled"}


@router.get("/plugins/{plugin_id}/settings")
async def get_plugin_settings(plugin_id: str):
    """Get plugin settings schema and current values."""
    registry = get_plugin_registry()

    plugin = registry.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(404, "Plugin not found")

    return {
        "plugin_id": plugin_id,
        "settings_schema": plugin.manifest.settings_schema,
        "current_settings": plugin.manifest.default_settings,
        "active_settings": (
            plugin.instance.settings if plugin.instance else plugin.manifest.default_settings
        ),
    }


# =============================================================================
# Marketplace Endpoints
# =============================================================================

@router.get("/marketplace/search", response_model=list[MarketplaceListingResponse])
async def search_marketplace(
    query: Optional[str] = Query(None),
    plugin_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    is_free: Optional[bool] = Query(None),
    sort_by: str = Query("downloads"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
):
    """Search the plugin marketplace."""
    marketplace = get_marketplace()
    listings = marketplace.search_listings(
        query=query,
        plugin_type=plugin_type,
        category=category,
        is_free=is_free,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )

    return [
        MarketplaceListingResponse(
            id=l.id,
            name=l.name,
            version=l.version,
            description=l.description,
            author=l.author,
            plugin_type=l.plugin_type,
            tags=l.tags,
            downloads=l.downloads,
            rating=l.rating,
            review_count=l.review_count,
            is_free=l.is_free,
            price_usd=l.price_usd,
            icon_url=l.icon_url,
            created_at=l.created_at,
        )
        for l in listings
    ]


@router.get("/marketplace/featured", response_model=list[MarketplaceListingResponse])
async def get_featured_plugins(limit: int = Query(10, le=50)):
    """Get featured marketplace plugins."""
    marketplace = get_marketplace()
    listings = marketplace.get_featured_listings(limit=limit)

    return [
        MarketplaceListingResponse(
            id=l.id, name=l.name, version=l.version,
            description=l.description, author=l.author,
            plugin_type=l.plugin_type, tags=l.tags,
            downloads=l.downloads, rating=l.rating,
            review_count=l.review_count, is_free=l.is_free,
            price_usd=l.price_usd, icon_url=l.icon_url,
            created_at=l.created_at,
        )
        for l in listings
    ]


@router.get("/marketplace/{listing_id}")
async def get_marketplace_listing(listing_id: str):
    """Get detailed marketplace listing."""
    marketplace = get_marketplace()
    listing = marketplace.get_listing(listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")
    return listing.to_dict()


@router.get("/marketplace/{listing_id}/reviews", response_model=list[ReviewResponse])
async def get_listing_reviews(listing_id: str, limit: int = Query(50)):
    """Get reviews for a marketplace listing."""
    marketplace = get_marketplace()
    reviews = marketplace.get_reviews(listing_id, limit=limit)

    return [
        ReviewResponse(
            id=r.id, rating=r.rating, title=r.title,
            body=r.body, user_name=r.user_name,
            created_at=r.created_at,
        )
        for r in reviews
    ]


@router.post("/marketplace/{listing_id}/reviews", response_model=ReviewResponse, status_code=201)
async def submit_review(listing_id: str, request: ReviewRequest):
    """Submit a review for a marketplace plugin."""
    marketplace = get_marketplace()

    listing = marketplace.get_listing(listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")

    review = PluginReview(
        id="",
        listing_id=listing_id,
        user_id="anonymous",
        user_name=request.user_name or "Anonymous",
        rating=request.rating,
        title=request.title,
        body=request.body,
    )

    review_id = marketplace.add_review(review)

    return ReviewResponse(
        id=review_id, rating=review.rating, title=review.title,
        body=review.body, user_name=review.user_name,
        created_at=review.created_at,
    )


@router.get("/marketplace/stats", response_model=MarketplaceStatsResponse)
async def get_marketplace_stats():
    """Get marketplace statistics."""
    marketplace = get_marketplace()
    stats = marketplace.get_marketplace_stats()
    return MarketplaceStatsResponse(**stats)


# =============================================================================
# Template Endpoints
# =============================================================================

@router.get("/templates", response_model=list[TemplateResponse])
async def list_templates(
    query: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    featured: Optional[bool] = Query(None),
    sort_by: str = Query("use_count"),
    limit: int = Query(50, le=100),
):
    """List community conversion templates."""
    marketplace = get_marketplace()
    templates = marketplace.search_templates(
        query=query,
        category=category,
        featured=featured,
        sort_by=sort_by,
        limit=limit,
    )

    return [
        TemplateResponse(
            id=t.id, name=t.name, description=t.description,
            author=t.author, category=t.category.value,
            config=t.config, use_count=t.use_count,
            rating=t.rating, is_featured=t.is_featured,
            tags=t.tags,
        )
        for t in templates
    ]


@router.get("/templates/featured", response_model=list[TemplateResponse])
async def get_featured_templates():
    """Get featured templates."""
    marketplace = get_marketplace()
    templates = marketplace.search_templates(featured=True)

    return [
        TemplateResponse(
            id=t.id, name=t.name, description=t.description,
            author=t.author, category=t.category.value,
            config=t.config, use_count=t.use_count,
            rating=t.rating, is_featured=t.is_featured,
            tags=t.tags,
        )
        for t in templates
    ]


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: str):
    """Get a specific template."""
    marketplace = get_marketplace()
    template = marketplace.get_template(template_id)
    if not template:
        raise HTTPException(404, "Template not found")

    return TemplateResponse(
        id=template.id, name=template.name,
        description=template.description, author=template.author,
        category=template.category.value, config=template.config,
        use_count=template.use_count, rating=template.rating,
        is_featured=template.is_featured, tags=template.tags,
    )


@router.post("/templates", response_model=TemplateResponse, status_code=201)
async def create_template(request: CreateTemplateRequest):
    """Create a new community template."""
    marketplace = get_marketplace()

    try:
        cat = TemplateCategory(request.category)
    except ValueError:
        cat = TemplateCategory.OTHER

    template = ConversionTemplate(
        id="",
        name=request.name,
        description=request.description,
        category=cat,
        config=request.config,
        tags=request.tags,
        author="Community",
    )

    template_id = marketplace.create_template(template)

    return TemplateResponse(
        id=template_id, name=template.name,
        description=template.description, author=template.author,
        category=template.category.value, config=template.config,
        use_count=0, rating=0.0,
        is_featured=False, tags=template.tags,
    )


@router.post("/templates/{template_id}/use")
async def use_template(template_id: str):
    """Record a template usage and return its config."""
    marketplace = get_marketplace()
    template = marketplace.get_template(template_id)
    if not template:
        raise HTTPException(404, "Template not found")

    marketplace.record_template_use(template_id)

    return {
        "template_id": template_id,
        "name": template.name,
        "config": template.config,
        "use_count": template.use_count,
    }
