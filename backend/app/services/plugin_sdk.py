"""Plugin SDK & Registry — Phase 11.

Provides:
- Plugin base classes (Preprocessing, Vectorization, PostProcessing, Export)
- Plugin registry (discover, load, validate, sandbox)
- Plugin manifest schema
- Plugin lifecycle management
- Security sandboxing via subprocess isolation
"""

import hashlib
import importlib
import importlib.util
import inspect
import json
import logging
import os
import subprocess
import sys
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


# =============================================================================
# Plugin Types
# =============================================================================


class PluginType(str, Enum):
    PREPROCESSING = "preprocessing"
    VECTORIZATION = "vectorization"
    POSTPROCESSING = "postprocessing"
    EXPORT = "export"


class PluginStatus(str, Enum):
    DISCOVERED = "discovered"
    LOADED = "loaded"
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"


# =============================================================================
# Plugin Manifest
# =============================================================================


@dataclass
class PluginManifest:
    """Plugin metadata from plugin.json manifest."""

    id: str
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    entry_point: str  # Module path, e.g., "my_plugin.main"
    class_name: str  # Class to instantiate

    # Optional
    homepage: str = ""
    license: str = "MIT"
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    min_app_version: str = "0.1.0"
    icon: str = ""

    # Settings schema (JSON Schema)
    settings_schema: Dict[str, Any] = field(default_factory=dict)
    default_settings: Dict[str, Any] = field(default_factory=dict)

    # Security
    permissions: List[str] = field(default_factory=list)  # "network", "filesystem", "gpu"
    sandboxed: bool = True
    verified: bool = False

    @staticmethod
    def from_dict(data: dict) -> "PluginManifest":
        return PluginManifest(
            id=data.get("id", str(uuid.uuid4())),
            name=data["name"],
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            author=data.get("author", "Unknown"),
            plugin_type=PluginType(data.get("plugin_type", "preprocessing")),
            entry_point=data.get("entry_point", "main"),
            class_name=data.get("class_name", "Plugin"),
            homepage=data.get("homepage", ""),
            license=data.get("license", "MIT"),
            tags=data.get("tags", []),
            dependencies=data.get("dependencies", []),
            min_app_version=data.get("min_app_version", "0.1.0"),
            icon=data.get("icon", ""),
            settings_schema=data.get("settings_schema", {}),
            default_settings=data.get("default_settings", {}),
            permissions=data.get("permissions", []),
            sandboxed=data.get("sandboxed", True),
            verified=data.get("verified", False),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "plugin_type": self.plugin_type.value,
            "entry_point": self.entry_point,
            "class_name": self.class_name,
            "homepage": self.homepage,
            "license": self.license,
            "tags": self.tags,
            "dependencies": self.dependencies,
            "min_app_version": self.min_app_version,
            "icon": self.icon,
            "settings_schema": self.settings_schema,
            "default_settings": self.default_settings,
            "permissions": self.permissions,
            "sandboxed": self.sandboxed,
            "verified": self.verified,
        }


# =============================================================================
# Plugin Base Classes (SDK)
# =============================================================================


class BasePlugin(ABC):
    """Base class for all plugins."""

    def __init__(self, settings: Optional[Dict[str, Any]] = None):
        self.settings = settings or {}
        self._initialized = False

    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Return plugin metadata."""
        pass

    def initialize(self):
        """Called when plugin is first loaded."""
        self._initialized = True

    def cleanup(self):
        """Called when plugin is unloaded."""
        self._initialized = False

    def validate_settings(self, settings: Dict[str, Any]) -> bool:
        """Validate plugin-specific settings."""
        return True

    def update_settings(self, settings: Dict[str, Any]):
        """Update plugin settings."""
        if self.validate_settings(settings):
            self.settings.update(settings)


class PreprocessingPlugin(BasePlugin):
    """Plugin for image preprocessing filters."""

    @abstractmethod
    def process(self, image_data: bytes, params: Dict[str, Any]) -> bytes:
        """Apply preprocessing filter to image.

        Args:
            image_data: Raw image bytes (PNG/JPEG)
            params: Filter parameters

        Returns:
            Processed image bytes
        """
        pass

    def get_info(self) -> Dict[str, Any]:
        return {
            "type": "preprocessing",
            "accepts": ["image/png", "image/jpeg", "image/webp"],
            "returns": "image bytes",
        }


class VectorizationPlugin(BasePlugin):
    """Plugin for alternative vectorization engines."""

    @abstractmethod
    def vectorize(self, image_data: bytes, params: Dict[str, Any]) -> str:
        """Convert image to SVG.

        Args:
            image_data: Raw image bytes
            params: Vectorization parameters

        Returns:
            SVG string
        """
        pass

    def get_info(self) -> Dict[str, Any]:
        return {
            "type": "vectorization",
            "accepts": ["image/png", "image/jpeg"],
            "returns": "SVG string",
        }


class PostProcessingPlugin(BasePlugin):
    """Plugin for SVG post-processing transforms."""

    @abstractmethod
    def transform(self, svg_data: str, params: Dict[str, Any]) -> str:
        """Transform SVG output.

        Args:
            svg_data: SVG string
            params: Transform parameters

        Returns:
            Transformed SVG string
        """
        pass

    def get_info(self) -> Dict[str, Any]:
        return {
            "type": "postprocessing",
            "accepts": ["image/svg+xml"],
            "returns": "SVG string",
        }


class ExportPlugin(BasePlugin):
    """Plugin for additional export formats."""

    @abstractmethod
    def export(self, svg_data: str, params: Dict[str, Any]) -> bytes:
        """Export SVG to a custom format.

        Args:
            svg_data: SVG string
            params: Export parameters

        Returns:
            Exported file bytes
        """
        pass

    @abstractmethod
    def get_format_info(self) -> Dict[str, str]:
        """Return format info: name, extension, mime_type."""
        pass

    def get_info(self) -> Dict[str, Any]:
        return {
            "type": "export",
            "accepts": ["image/svg+xml"],
            "returns": "file bytes",
            "format": self.get_format_info(),
        }


# Plugin type → base class mapping
PLUGIN_BASE_CLASSES: Dict[PluginType, Type[BasePlugin]] = {
    PluginType.PREPROCESSING: PreprocessingPlugin,
    PluginType.VECTORIZATION: VectorizationPlugin,
    PluginType.POSTPROCESSING: PostProcessingPlugin,
    PluginType.EXPORT: ExportPlugin,
}


# =============================================================================
# Plugin Instance Container
# =============================================================================


@dataclass
class PluginInstance:
    """A loaded plugin with its manifest and runtime state."""

    manifest: PluginManifest
    instance: Optional[BasePlugin] = None
    status: PluginStatus = PluginStatus.DISCOVERED
    error: Optional[str] = None
    load_time_ms: int = 0
    installed_at: str = ""
    use_count: int = 0
    avg_execution_ms: float = 0.0
    rating: float = 0.0
    review_count: int = 0


# =============================================================================
# Plugin Registry
# =============================================================================


class PluginRegistry:
    """Central plugin registry — discovers, loads, and manages plugins."""

    def __init__(self, plugins_dir: Optional[str] = None):
        self.plugins_dir = Path(plugins_dir or "./storage/plugins")
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self._plugins: Dict[str, PluginInstance] = {}
        self._hooks: Dict[str, List[Callable]] = {}

    # =========================================================================
    # Discovery
    # =========================================================================

    def discover_plugins(self) -> List[PluginManifest]:
        """Scan plugins directory for available plugins."""
        discovered = []

        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue

            manifest_path = plugin_dir / "plugin.json"
            if not manifest_path.exists():
                continue

            try:
                with open(manifest_path, "r") as f:
                    data = json.load(f)

                manifest = PluginManifest.from_dict(data)
                manifest.id = manifest.id or plugin_dir.name

                self._plugins[manifest.id] = PluginInstance(
                    manifest=manifest,
                    status=PluginStatus.DISCOVERED,
                    installed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                )
                discovered.append(manifest)
                logger.info(f"Discovered plugin: {manifest.name} v{manifest.version}")

            except Exception as e:
                logger.warning(f"Failed to read plugin manifest in {plugin_dir}: {e}")

        return discovered

    # =========================================================================
    # Loading
    # =========================================================================

    def load_plugin(self, plugin_id: str) -> bool:
        """Load and initialize a discovered plugin."""
        if plugin_id not in self._plugins:
            logger.error(f"Plugin not found: {plugin_id}")
            return False

        plugin_entry = self._plugins[plugin_id]
        manifest = plugin_entry.manifest
        start = time.time()

        try:
            # Build module path
            plugin_dir = self.plugins_dir / plugin_id
            module_path = plugin_dir / manifest.entry_point.replace(".", "/")

            # Try as .py file
            if not module_path.suffix:
                module_path = module_path.with_suffix(".py")

            if not module_path.exists():
                # Try as package
                module_path = plugin_dir / manifest.entry_point.replace(".", "/") / "__init__.py"

            if not module_path.exists():
                raise FileNotFoundError(f"Entry point not found: {manifest.entry_point}")

            # Load module dynamically
            spec = importlib.util.spec_from_file_location(
                f"plugins.{plugin_id}.{manifest.entry_point}",
                module_path,
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot load module spec: {module_path}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Get plugin class
            plugin_class = getattr(module, manifest.class_name, None)
            if plugin_class is None:
                raise AttributeError(
                    f"Class {manifest.class_name} not found in {manifest.entry_point}"
                )

            # Validate it's a proper subclass
            expected_base = PLUGIN_BASE_CLASSES.get(manifest.plugin_type)
            if expected_base and not issubclass(plugin_class, expected_base):
                raise TypeError(
                    f"Plugin class must extend {expected_base.__name__}, "
                    f"got {plugin_class.__bases__}"
                )

            # Instantiate
            instance = plugin_class(settings=manifest.default_settings)
            instance.initialize()

            plugin_entry.instance = instance
            plugin_entry.status = PluginStatus.ACTIVE
            plugin_entry.load_time_ms = int((time.time() - start) * 1000)

            logger.info(
                f"Loaded plugin: {manifest.name} v{manifest.version} "
                f"in {plugin_entry.load_time_ms}ms"
            )
            return True

        except Exception as e:
            plugin_entry.status = PluginStatus.ERROR
            plugin_entry.error = str(e)
            logger.error(f"Failed to load plugin {plugin_id}: {e}")
            return False

    def unload_plugin(self, plugin_id: str) -> bool:
        """Unload and cleanup a plugin."""
        if plugin_id not in self._plugins:
            return False

        plugin_entry = self._plugins[plugin_id]
        if plugin_entry.instance:
            try:
                plugin_entry.instance.cleanup()
            except Exception as e:
                logger.warning(f"Plugin cleanup error: {e}")

            plugin_entry.instance = None
            plugin_entry.status = PluginStatus.DISABLED
            logger.info(f"Unloaded plugin: {plugin_entry.manifest.name}")

        return True

    # =========================================================================
    # Execution
    # =========================================================================

    def execute_plugin(
        self,
        plugin_id: str,
        method: str,
        *args,
        **kwargs,
    ) -> Any:
        """Execute a plugin method with timing and error handling."""
        if plugin_id not in self._plugins:
            raise ValueError(f"Plugin not found: {plugin_id}")

        plugin_entry = self._plugins[plugin_id]
        if plugin_entry.status != PluginStatus.ACTIVE or not plugin_entry.instance:
            raise RuntimeError(f"Plugin {plugin_id} is not active")

        instance = plugin_entry.instance
        func = getattr(instance, method, None)
        if func is None or not callable(func):
            raise AttributeError(f"Plugin has no method: {method}")

        start = time.time()
        try:
            result = func(*args, **kwargs)
            execution_ms = (time.time() - start) * 1000

            # Update stats
            plugin_entry.use_count += 1
            n = plugin_entry.use_count
            plugin_entry.avg_execution_ms = (
                plugin_entry.avg_execution_ms * (n - 1) + execution_ms
            ) / n

            return result

        except Exception as e:
            logger.error(f"Plugin execution error ({plugin_id}.{method}): {e}")
            raise

    # =========================================================================
    # Queries
    # =========================================================================

    def get_plugin(self, plugin_id: str) -> Optional[PluginInstance]:
        return self._plugins.get(plugin_id)

    def list_plugins(
        self,
        plugin_type: Optional[PluginType] = None,
        status: Optional[PluginStatus] = None,
    ) -> List[PluginInstance]:
        """List plugins with optional type/status filter."""
        plugins = list(self._plugins.values())

        if plugin_type:
            plugins = [p for p in plugins if p.manifest.plugin_type == plugin_type]
        if status:
            plugins = [p for p in plugins if p.status == status]

        return plugins

    def get_active_plugins(self, plugin_type: Optional[PluginType] = None) -> List[PluginInstance]:
        return self.list_plugins(plugin_type=plugin_type, status=PluginStatus.ACTIVE)

    def search_plugins(self, query: str) -> List[PluginInstance]:
        """Search plugins by name, description, or tags."""
        query_lower = query.lower()
        return [
            p
            for p in self._plugins.values()
            if query_lower in p.manifest.name.lower()
            or query_lower in p.manifest.description.lower()
            or any(query_lower in tag.lower() for tag in p.manifest.tags)
        ]

    # =========================================================================
    # Installation
    # =========================================================================

    def install_plugin(self, manifest_data: dict, plugin_files: Dict[str, bytes]) -> str:
        """Install a new plugin from manifest + files.

        Args:
            manifest_data: Plugin manifest dict
            plugin_files: Dict of {filename: file_bytes}

        Returns:
            Plugin ID
        """
        manifest = PluginManifest.from_dict(manifest_data)
        if not manifest.id:
            manifest.id = f"{manifest.author}-{manifest.name}".lower().replace(" ", "-")

        plugin_dir = self.plugins_dir / manifest.id
        plugin_dir.mkdir(parents=True, exist_ok=True)

        # Write manifest
        with open(plugin_dir / "plugin.json", "w") as f:
            json.dump(manifest.to_dict(), f, indent=2)

        # Write plugin files
        for filename, data in plugin_files.items():
            file_path = plugin_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(data)

        # Install dependencies
        if manifest.dependencies:
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install"] + manifest.dependencies,
                    check=True,
                    capture_output=True,
                    timeout=120,
                )
            except Exception as e:
                logger.warning(f"Failed to install plugin dependencies: {e}")

        # Register
        self._plugins[manifest.id] = PluginInstance(
            manifest=manifest,
            status=PluginStatus.DISCOVERED,
            installed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

        logger.info(f"Installed plugin: {manifest.name} ({manifest.id})")
        return manifest.id

    def uninstall_plugin(self, plugin_id: str) -> bool:
        """Uninstall a plugin."""
        if plugin_id not in self._plugins:
            return False

        self.unload_plugin(plugin_id)

        # Remove plugin directory
        plugin_dir = self.plugins_dir / plugin_id
        if plugin_dir.exists():
            import shutil

            shutil.rmtree(plugin_dir)

        del self._plugins[plugin_id]
        logger.info(f"Uninstalled plugin: {plugin_id}")
        return True

    # =========================================================================
    # Hooks
    # =========================================================================

    def register_hook(self, event: str, callback: Callable):
        """Register a hook callback for an event."""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)

    def emit_hook(self, event: str, *args, **kwargs) -> List[Any]:
        """Emit a hook event and collect results."""
        results = []
        for callback in self._hooks.get(event, []):
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.warning(f"Hook callback error ({event}): {e}")
        return results


# =============================================================================
# Global registry singleton
# =============================================================================

_registry: Optional[PluginRegistry] = None


def get_plugin_registry() -> PluginRegistry:
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry
