"""Service for managing batch processing templates."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path
import re

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class BatchTemplate(BaseModel):
    """Template for batch processing configuration."""
    id: str
    name: str
    description: str
    
    # File naming pattern
    output_pattern: str = "{original}_{timestamp}.svg"
    
    # Conversion settings
    control_level: int = 2
    quality_mode: str = "standard"
    image_type: str = "auto"
    color_palette: int = 32
    denoise_strength: str = "medium"
    
    # Advanced settings (for level 3)
    preprocessing_config: Optional[Dict[str, Any]] = None
    palette_config: Optional[Dict[str, Any]] = None
    vectorization_config: Optional[Dict[str, Any]] = None
    output_config: Optional[Dict[str, Any]] = None
    
    # Filter settings
    file_filter: Optional[str] = None  # Regex pattern for file filtering
    max_file_size: Optional[int] = None  # Maximum file size in bytes
    skip_existing: bool = False  # Skip files that already have output
    
    # Organization
    preserve_structure: bool = True  # Preserve directory structure
    output_subfolder: Optional[str] = None  # Subfolder for output
    
    # Created/Updated
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    use_count: int = 0


class BatchTemplateService:
    """Service for managing batch processing templates."""
    
    def __init__(self):
        self.templates: Dict[str, BatchTemplate] = {}
        self._load_builtin_templates()
    
    def _load_builtin_templates(self):
    """Load built-in batch templates."""
        builtin_templates = [
            BatchTemplate(
                id="logo-batch",
                name="Logo Batch Processing",
                description="Optimized for logo files with transparent backgrounds",
                output_pattern="{original}_vector.svg",
                control_level=3,
                quality_mode="high",
                image_type="color",
                color_palette=64,
                preprocessing_config={
                    "steps": [
                        {"name": "denoise", "enabled": True, "params": {"method": "bilateral", "strength": "light"}},
                        {"name": "color_reduce", "enabled": True, "params": {"max_colors": 64}},
                    ]
                },
                output_config={
                    "optimization_level": "aggressive",
                    "remove_metadata": True,
                },
                file_filter=r".*\.(png|svg)$",
            ),
            BatchTemplate(
                id="photo-batch",
                name="Photo Batch Processing",
                description="Balanced settings for photograph collections",
                output_pattern="{original}_{timestamp}.svg",
                control_level=2,
                quality_mode="standard",
                image_type="color",
                color_palette=32,
                denoise_strength="medium",
                preserve_structure=True,
            ),
            BatchTemplate(
                id="document-batch",
                name="Document Scan Batch",
                description="Optimized for scanned documents and text",
                output_pattern="{original}_clean.svg",
                control_level=3,
                quality_mode="high",
                image_type="monochrome",
                preprocessing_config={
                    "steps": [
                        {"name": "denoise", "enabled": True, "params": {"method": "nlm", "strength": "medium"}},
                        {"name": "contrast", "enabled": True, "params": {"method": "clahe"}},
                        {"name": "deskew", "enabled": True, "params": {"auto_detect": True}},
                    ]
                },
                file_filter=r".*\.(pdf|tiff?|png)$",
            ),
            BatchTemplate(
                id="archive-batch",
                name="Archive Processing",
                description="Maximum quality for archival purposes",
                output_pattern="{original}_archive.svg",
                control_level=3,
                quality_mode="high",
                image_type="auto",
                color_palette=128,
                preprocessing_config={
                    "steps": [
                        {"name": "denoise", "enabled": True, "params": {"method": "nlm", "strength": "heavy"}},
                        {"name": "sharpen", "enabled": True, "params": {"amount": 1.5}},
                        {"name": "contrast", "enabled": True, "params": {"method": "clahe", "clip_limit": 3}},
                    ]
                },
                output_config={
                    "precision": 3,
                    "optimization_level": "light",
                },
            ),
            BatchTemplate(
                id="web-optimization",
                name="Web Optimization",
                description="Aggressive optimization for web use",
                output_pattern="{original}_web.svg",
                control_level=2,
                quality_mode="standard",
                image_type="color",
                color_palette=16,
                output_config={
                    "optimization_level": "aggressive",
                    "minify": True,
                    "remove_metadata": True,
                    "precision": 1,
                },
                max_file_size=10 * 1024 * 1024,  # 10MB
            ),
        ]
        
        for template in builtin_templates:
            self.templates[template.id] = template
            template.use_count = 0  # Built-in templates start at 0
    
    def create_template(self, template: BatchTemplate) -> BatchTemplate:
        """Create a new batch template."""
        self.templates[template.id] = template
        logger.info(f"Created batch template: {template.id}")
        return template
    
    def get_template(self, template_id: str) -> Optional[BatchTemplate]:
        """Get template by ID."""
        return self.templates.get(template_id)
    
    def list_templates(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[BatchTemplate]:
        """List batch templates."""
        templates = list(self.templates.values())
        
        if category:
            # Built-in templates have use_count 0, user templates have use_count > 0
            is_builtin = category == "built_in"
            templates = [t for t in templates if (t.use_count == 0) == is_builtin]
        
        if search:
            search_lower = search.lower()
            templates = [
                t for t in templates
                if search_lower in t.name.lower()
                or search_lower in t.description.lower()
            ]
        
        # Sort by use count (most used first) then by name
        templates.sort(key=lambda t: (-t.use_count, t.name))
        
        return templates
    
    def update_template(
        self,
        template_id: str,
        updates: Dict[str, Any],
    ) -> Optional[BatchTemplate]:
        """Update a batch template."""
        template = self.templates.get(template_id)
        if not template:
            return None
        
        # Prevent updates to built-in templates (use_count == 0)
        if template.use_count == 0:
            raise ValueError("Cannot modify built-in templates")
        
        for key, value in updates.items():
            if hasattr(template, key):
                setattr(template, key, value)
        
        template.updated_at = datetime.now(timezone.utc)
        logger.info(f"Updated batch template: {template_id}")
        return template
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a batch template."""
        template = self.templates.get(template_id)
        if not template:
            return False
        
        # Prevent deletion of built-in templates
        if template.use_count == 0:
            raise ValueError("Cannot delete built-in templates")
        
        del self.templates[template_id]
        logger.info(f"Deleted batch template: {template_id}")
        return True
    
    def increment_use_count(self, template_id: str):
        """Increment the use count of a template."""
        template = self.templates.get(template_id)
        if template:
            template.use_count += 1
    
    def apply_template(
        self,
        template_id: str,
        file_paths: List[Path],
        output_dir: Path,
    ) -> Dict[str, Any]:
        """Apply a template to a list of files."""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        # Filter files
        filtered_files = self._filter_files(file_paths, template)
        
        # Generate output paths
        output_paths = []
        for file_path in filtered_files:
            output_name = self._generate_output_name(file_path, template)
            
            if template.preserve_structure:
                # Preserve directory structure
                relative_path = file_path.relative_to(file_path.parent.parent if file_path.parent.parent.exists() else file_path.parent)
                output_path = output_dir / relative_path.parent / output_name
            else:
                output_path = output_dir / output_name
            
            if template.output_subfolder:
                output_path = output_dir / template.output_subfolder / output_name
            
            # Check if should skip existing
            if template.skip_existing and output_path.exists():
                continue
            
            output_paths.append({
                "input": file_path,
                "output": output_path,
            })
        
        self.increment_use_count(template_id)
        
        return {
            "template_id": template_id,
            "total_files": len(file_paths),
            "filtered_files": len(filtered_files),
            "output_files": output_paths,
            "settings": {
                "control_level": template.control_level,
                "quality_mode": template.quality_mode,
                "image_type": template.image_type,
            },
        }
    
    def _filter_files(
        self,
        file_paths: List[Path],
        template: BatchTemplate,
    ) -> List[Path]:
        """Filter files based on template criteria."""
        filtered = file_paths
        
        # Filter by regex pattern
        if template.file_filter:
            pattern = re.compile(template.file_filter, re.IGNORECASE)
            filtered = [f for f in filtered if pattern.match(f.name)]
        
        # Filter by file size
        if template.max_file_size:
            filtered = [
                f for f in filtered
                if f.exists() and f.stat().st_size <= template.max_file_size
            ]
        
        return filtered
    
    def _generate_output_name(self, input_path: Path, template: BatchTemplate) -> str:
        """Generate output filename based on pattern."""
        pattern = template.output_pattern
        
        # Extract name without extension
        original_name = input_path.stem
        
        # Replace placeholders
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        output_name = pattern.replace("{original}", original_name)
        output_name = output_name.replace("{timestamp}", timestamp)
        output_name = output_name.replace("{quality}", template.quality_mode)
        
        # Ensure .svg extension
        if not output_name.endswith('.svg'):
            output_name += '.svg'
        
        return output_name
    
    def get_conversion_options(self, template_id: str) -> Dict[str, Any]:
        """Get conversion options from a template."""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        options = {
            "control_level": template.control_level,
            "quality_mode": template.quality_mode,
            "image_type": template.image_type,
        }
        
        if template.control_level >= 2:
            options["color_palette"] = template.color_palette
            options["denoise_strength"] = template.denoise_strength
        
        if template.control_level >= 3:
            if template.preprocessing_config:
                options["preprocessing"] = template.preprocessing_config
            if template.palette_config:
                options["palette_config"] = template.palette_config
            if template.vectorization_config:
                options["vectorization"] = template.vectorization_config
            if template.output_config:
                options["output_config"] = template.output_config
        
        return options


# Global instance
_template_service: Optional[BatchTemplateService] = None


def get_batch_template_service() -> BatchTemplateService:
    """Get or create global batch template service."""
    global _template_service
    if _template_service is None:
        _template_service = BatchTemplateService()
    return _template_service
