"""Marketplace service — Phase 11.

Manages the plugin marketplace:
- In-memory marketplace index (upgradeable to database)
- Plugin publishing & review
- Version management
- Download tracking & ratings
- Community template library
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# =============================================================================
# Marketplace Models
# =============================================================================


class ListingStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    PUBLISHED = "published"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"


class TemplateCategory(str, Enum):
    LOGO = "logo"
    ICON = "icon"
    ILLUSTRATION = "illustration"
    PHOTO = "photo"
    TECHNICAL = "technical"
    ART = "art"
    TEXT = "text"
    OTHER = "other"


@dataclass
class MarketplaceListing:
    """A plugin listing in the marketplace."""

    id: str
    plugin_id: str
    name: str
    version: str
    description: str
    long_description: str = ""
    author: str = ""
    author_id: str = ""
    plugin_type: str = "preprocessing"
    status: ListingStatus = ListingStatus.DRAFT

    # Discovery
    tags: List[str] = field(default_factory=list)
    category: str = "other"
    screenshots: List[str] = field(default_factory=list)
    icon_url: str = ""

    # Stats
    downloads: int = 0
    rating: float = 0.0
    review_count: int = 0

    # Pricing
    is_free: bool = True
    price_usd: float = 0.0

    # Metadata
    homepage: str = ""
    repository: str = ""
    license: str = "MIT"
    min_app_version: str = "0.1.0"
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "plugin_id": self.plugin_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "long_description": self.long_description,
            "author": self.author,
            "author_id": self.author_id,
            "plugin_type": self.plugin_type,
            "status": self.status.value,
            "tags": self.tags,
            "category": self.category,
            "screenshots": self.screenshots,
            "icon_url": self.icon_url,
            "downloads": self.downloads,
            "rating": self.rating,
            "review_count": self.review_count,
            "is_free": self.is_free,
            "price_usd": self.price_usd,
            "homepage": self.homepage,
            "repository": self.repository,
            "license": self.license,
            "min_app_version": self.min_app_version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class PluginReview:
    """A user review for a marketplace plugin."""

    id: str
    listing_id: str
    user_id: str
    user_name: str = ""
    rating: int = 5  # 1-5
    title: str = ""
    body: str = ""
    created_at: str = ""


@dataclass
class ConversionTemplate:
    """A community conversion template / preset."""

    id: str
    name: str
    description: str
    author: str = ""
    author_id: str = ""
    category: TemplateCategory = TemplateCategory.OTHER

    # Template config
    config: Dict[str, Any] = field(default_factory=dict)
    # Example config: {
    #   "engine": "vtracer",
    #   "quality_mode": "quality",
    #   "preprocessing": {"denoise": true, "sharpen": 0.5},
    #   "ai_mode": "balanced",
    #   "export_format": "svg"
    # }

    # Sample images
    sample_input_url: str = ""
    sample_output_url: str = ""

    # Stats
    use_count: int = 0
    rating: float = 0.0
    is_featured: bool = False
    tags: List[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "author_id": self.author_id,
            "category": self.category.value,
            "config": self.config,
            "sample_input_url": self.sample_input_url,
            "sample_output_url": self.sample_output_url,
            "use_count": self.use_count,
            "rating": self.rating,
            "is_featured": self.is_featured,
            "tags": self.tags,
            "created_at": self.created_at,
        }


# =============================================================================
# Marketplace Service
# =============================================================================


class MarketplaceService:
    """Plugin marketplace management service."""

    def __init__(self):
        self._listings: Dict[str, MarketplaceListing] = {}
        self._reviews: Dict[str, List[PluginReview]] = {}
        self._templates: Dict[str, ConversionTemplate] = {}
        self._seed_templates()

    # =========================================================================
    # Plugin Listings
    # =========================================================================

    def publish_listing(self, listing: MarketplaceListing) -> str:
        """Publish or update a marketplace listing."""
        if not listing.id:
            listing.id = str(uuid.uuid4())

        now = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        if not listing.created_at:
            listing.created_at = now
        listing.updated_at = now
        listing.status = ListingStatus.SUBMITTED

        self._listings[listing.id] = listing
        logger.info(f"Listing submitted: {listing.name} by {listing.author}")
        return listing.id

    def approve_listing(self, listing_id: str) -> bool:
        """Approve a submitted listing for publication."""
        listing = self._listings.get(listing_id)
        if not listing:
            return False
        listing.status = ListingStatus.PUBLISHED
        listing.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        return True

    def reject_listing(self, listing_id: str, reason: str = "") -> bool:
        """Reject a submitted listing."""
        listing = self._listings.get(listing_id)
        if not listing:
            return False
        listing.status = ListingStatus.REJECTED
        listing.long_description += f"\n\n[Rejection reason: {reason}]"
        return True

    def get_listing(self, listing_id: str) -> Optional[MarketplaceListing]:
        return self._listings.get(listing_id)

    def search_listings(
        self,
        query: Optional[str] = None,
        plugin_type: Optional[str] = None,
        category: Optional[str] = None,
        is_free: Optional[bool] = None,
        sort_by: str = "downloads",
        limit: int = 50,
        offset: int = 0,
    ) -> List[MarketplaceListing]:
        """Search marketplace listings."""
        results = [l for l in self._listings.values() if l.status == ListingStatus.PUBLISHED]

        if query:
            q = query.lower()
            results = [
                l
                for l in results
                if q in l.name.lower()
                or q in l.description.lower()
                or any(q in t.lower() for t in l.tags)
            ]

        if plugin_type:
            results = [l for l in results if l.plugin_type == plugin_type]

        if category:
            results = [l for l in results if l.category == category]

        if is_free is not None:
            results = [l for l in results if l.is_free == is_free]

        # Sort
        sort_key = {
            "downloads": lambda l: l.downloads,
            "rating": lambda l: l.rating,
            "newest": lambda l: l.created_at,
            "name": lambda l: l.name.lower(),
        }.get(sort_by, lambda l: l.downloads)

        results.sort(key=sort_key, reverse=(sort_by != "name"))

        return results[offset : offset + limit]

    def get_featured_listings(self, limit: int = 10) -> List[MarketplaceListing]:
        """Get top-rated published listings."""
        published = [l for l in self._listings.values() if l.status == ListingStatus.PUBLISHED]
        published.sort(key=lambda l: (l.rating * l.review_count, l.downloads), reverse=True)
        return published[:limit]

    def record_download(self, listing_id: str):
        """Increment download count."""
        listing = self._listings.get(listing_id)
        if listing:
            listing.downloads += 1

    # =========================================================================
    # Reviews
    # =========================================================================

    def add_review(self, review: PluginReview) -> str:
        """Add a review to a listing."""
        if not review.id:
            review.id = str(uuid.uuid4())
        review.created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ")

        if review.listing_id not in self._reviews:
            self._reviews[review.listing_id] = []
        self._reviews[review.listing_id].append(review)

        # Update listing rating
        self._update_listing_rating(review.listing_id)

        return review.id

    def get_reviews(self, listing_id: str, limit: int = 50) -> List[PluginReview]:
        return self._reviews.get(listing_id, [])[:limit]

    def _update_listing_rating(self, listing_id: str):
        reviews = self._reviews.get(listing_id, [])
        listing = self._listings.get(listing_id)
        if listing and reviews:
            listing.review_count = len(reviews)
            listing.rating = sum(r.rating for r in reviews) / len(reviews)

    # =========================================================================
    # Templates
    # =========================================================================

    def create_template(self, template: ConversionTemplate) -> str:
        """Create a new conversion template."""
        if not template.id:
            template.id = str(uuid.uuid4())
        template.created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        self._templates[template.id] = template
        logger.info(f"Template created: {template.name}")
        return template.id

    def get_template(self, template_id: str) -> Optional[ConversionTemplate]:
        return self._templates.get(template_id)

    def search_templates(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        featured: Optional[bool] = None,
        sort_by: str = "use_count",
        limit: int = 50,
    ) -> List[ConversionTemplate]:
        """Search conversion templates."""
        results = list(self._templates.values())

        if query:
            q = query.lower()
            results = [
                t
                for t in results
                if q in t.name.lower()
                or q in t.description.lower()
                or any(q in tag.lower() for tag in t.tags)
            ]

        if category:
            results = [t for t in results if t.category.value == category]

        if featured is not None:
            results = [t for t in results if t.is_featured == featured]

        sort_key = {
            "use_count": lambda t: t.use_count,
            "rating": lambda t: t.rating,
            "newest": lambda t: t.created_at,
        }.get(sort_by, lambda t: t.use_count)

        results.sort(key=sort_key, reverse=True)
        return results[:limit]

    def record_template_use(self, template_id: str):
        """Increment template use count."""
        template = self._templates.get(template_id)
        if template:
            template.use_count += 1

    # =========================================================================
    # Marketplace Stats
    # =========================================================================

    def get_marketplace_stats(self) -> Dict[str, Any]:
        """Get overall marketplace statistics."""
        published = [l for l in self._listings.values() if l.status == ListingStatus.PUBLISHED]
        return {
            "total_plugins": len(published),
            "total_templates": len(self._templates),
            "total_downloads": sum(l.downloads for l in published),
            "total_reviews": sum(len(reviews) for reviews in self._reviews.values()),
            "avg_rating": (sum(l.rating for l in published) / len(published) if published else 0),
            "plugins_by_type": {
                pt: len([l for l in published if l.plugin_type == pt])
                for pt in ["preprocessing", "vectorization", "postprocessing", "export"]
            },
            "free_plugins": len([l for l in published if l.is_free]),
            "paid_plugins": len([l for l in published if not l.is_free]),
        }

    # =========================================================================
    # Seed Data
    # =========================================================================

    def _seed_templates(self):
        """Seed marketplace with built-in community templates."""
        templates = [
            ConversionTemplate(
                id="tpl-logo-clean",
                name="Clean Logo",
                description="Best settings for clean, simple logos with solid colors and sharp edges.",
                author="Raster to SVG Team",
                category=TemplateCategory.LOGO,
                config={
                    "engine": "vtracer",
                    "quality_mode": "quality",
                    "color_mode": "color",
                    "preprocessing": {"denoise": True, "sharpen": 0.3, "threshold": False},
                    "filter_speckle": 4,
                    "corner_threshold": 60,
                    "segment_length": 3.5,
                },
                use_count=1240,
                rating=4.8,
                is_featured=True,
                tags=["logo", "brand", "clean", "corporate"],
            ),
            ConversionTemplate(
                id="tpl-photo-artistic",
                name="Artistic Photo",
                description="Convert photographs into artistic vector illustrations with color reduction.",
                author="Raster to SVG Team",
                category=TemplateCategory.PHOTO,
                config={
                    "engine": "vtracer",
                    "quality_mode": "balanced",
                    "color_mode": "color",
                    "preprocessing": {"color_reduce": 16, "denoise": True, "contrast": 1.2},
                    "filter_speckle": 2,
                    "color_precision": 6,
                    "gradient_step": 64,
                },
                use_count=890,
                rating=4.5,
                is_featured=True,
                tags=["photo", "artistic", "illustration", "portrait"],
            ),
            ConversionTemplate(
                id="tpl-icon-pixel",
                name="Pixel-Perfect Icon",
                description="Optimized for small icons and UI elements — crisp edges, minimal paths.",
                author="Raster to SVG Team",
                category=TemplateCategory.ICON,
                config={
                    "engine": "vtracer",
                    "quality_mode": "speed",
                    "color_mode": "color",
                    "preprocessing": {"sharpen": 0.6, "denoise": False},
                    "filter_speckle": 8,
                    "corner_threshold": 90,
                    "path_precision": 2,
                },
                use_count=2100,
                rating=4.9,
                is_featured=True,
                tags=["icon", "ui", "pixel", "crisp", "app"],
            ),
            ConversionTemplate(
                id="tpl-line-art",
                name="Line Art / Sketch",
                description="Perfect for hand-drawn sketches, pen drawings, and line art.",
                author="Raster to SVG Team",
                category=TemplateCategory.ART,
                config={
                    "engine": "vtracer",
                    "quality_mode": "quality",
                    "color_mode": "bw",
                    "preprocessing": {"threshold": True, "threshold_value": 128, "invert": False},
                    "filter_speckle": 2,
                    "corner_threshold": 45,
                },
                use_count=760,
                rating=4.7,
                is_featured=True,
                tags=["line art", "sketch", "drawing", "pen", "ink"],
            ),
            ConversionTemplate(
                id="tpl-technical-cad",
                name="Technical Drawing",
                description="For engineering diagrams, floor plans, and technical drawings with DXF export.",
                author="Raster to SVG Team",
                category=TemplateCategory.TECHNICAL,
                config={
                    "engine": "vtracer",
                    "quality_mode": "quality",
                    "color_mode": "bw",
                    "preprocessing": {"threshold": True, "sharpen": 0.8, "denoise": True},
                    "filter_speckle": 6,
                    "corner_threshold": 80,
                    "export_format": "dxf",
                },
                use_count=430,
                rating=4.6,
                is_featured=False,
                tags=["technical", "engineering", "cad", "blueprint", "diagram"],
            ),
            ConversionTemplate(
                id="tpl-illustration-rich",
                name="Rich Illustration",
                description="Maximum quality for complex illustrations with many colors and fine detail.",
                author="Raster to SVG Team",
                category=TemplateCategory.ILLUSTRATION,
                config={
                    "engine": "vtracer",
                    "quality_mode": "max_quality",
                    "color_mode": "color",
                    "preprocessing": {"denoise": True, "contrast": 1.1},
                    "filter_speckle": 1,
                    "color_precision": 8,
                    "corner_threshold": 30,
                },
                use_count=560,
                rating=4.4,
                is_featured=False,
                tags=["illustration", "detailed", "complex", "colorful"],
            ),
        ]

        for t in templates:
            t.created_at = "2026-01-01T00:00:00Z"
            self._templates[t.id] = t


# =============================================================================
# Global marketplace singleton
# =============================================================================

_marketplace: Optional[MarketplaceService] = None


def get_marketplace() -> MarketplaceService:
    global _marketplace
    if _marketplace is None:
        _marketplace = MarketplaceService()
    return _marketplace
