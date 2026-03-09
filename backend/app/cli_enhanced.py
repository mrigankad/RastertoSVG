"""Enhanced CLI with config file support and advanced features."""

import json
import sys
import time
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.services.converter import Converter
from app.services.preprocessor import Preprocessor
from app.services.preprocessing_pipeline import PreprocessingPipelineBuilder
from app.services.quality_analyzer import QualityAnalyzer

app = typer.Typer(
    name="raster-to-svg",
    help="Convert raster images to vector SVG format with advanced controls",
    no_args_is_help=True,
)
console = Console()

# Default config locations
CONFIG_LOCATIONS = [
    Path(".raster-to-svg.yaml"),
    Path(".raster-to-svg.yml"),
    Path(".raster-to-svg.json"),
    Path.home() / ".config" / "raster-to-svg" / "config.yaml",
    Path.home() / ".raster-to-svg.yaml",
]


class ConfigManager:
    """Manage configuration files."""
    
    @staticmethod
    def find_config() -> Optional[Path]:
        """Find configuration file in standard locations."""
        for location in CONFIG_LOCATIONS:
            if location.exists():
                return location
        return None
    
    @staticmethod
    def load_config(path: Path) -> Dict:
        """Load configuration from file."""
        with open(path, 'r') as f:
            if path.suffix in ['.yaml', '.yml']:
                return yaml.safe_load(f)
            elif path.suffix == '.json':
                return json.load(f)
            else:
                raise ValueError(f"Unsupported config format: {path.suffix}")
    
    @staticmethod
    def save_config(path: Path, config: Dict):
        """Save configuration to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            if path.suffix in ['.yaml', '.yml']:
                yaml.dump(config, f, default_flow_style=False)
            elif path.suffix == '.json':
                json.dump(config, f, indent=2)
    
    @staticmethod
    def get_default_config() -> Dict:
        """Get default configuration."""
        return {
            "version": "1.0",
            "defaults": {
                "quality_mode": "standard",
                "image_type": "auto",
                "color_palette": 32,
                "denoise_strength": "medium",
            },
            "preprocessing": {
                "steps": []
            },
            "vectorization": {
                "engine": "auto",
                "curve_fitting": "auto",
                "corner_threshold": 60,
                "path_precision": 2,
                "color_mode": "color",
                "hierarchical": True,
                "simplify_paths": True,
                "smooth_corners": True,
                "remove_small_paths": True,
                "min_path_area": 5,
            },
            "output": {
                "optimization_level": "standard",
                "precision": 2,
                "remove_metadata": True,
                "minify": False,
            },
            "batch": {
                "output_pattern": "{original}.svg",
                "preserve_structure": True,
                "skip_existing": False,
            }
        }


@app.command()
def convert(
    input_file: str = typer.Argument(..., help="Input raster image path"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Output SVG file path"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Configuration file path"),
    quality: str = typer.Option("standard", "--quality", "-q", help="Quality mode: fast, standard, high"),
    image_type: str = typer.Option("auto", "--type", "-t", help="Image type: auto, color, monochrome"),
    color_palette: int = typer.Option(32, "--colors", help="Maximum colors (8-256)"),
    denoise_strength: str = typer.Option("medium", "--denoise", "-d", help="Denoise: light, medium, heavy"),
    preset: Optional[str] = typer.Option(None, "--preset", "-p", help="Use a preset configuration"),
    preview: bool = typer.Option(False, "--preview", help="Generate preview only"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Watch for file changes"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without executing"),
):
    """Convert a single raster image to SVG with advanced options."""
    input_path = Path(input_file)
    
    if not input_path.exists():
        console.print(f"[red]Error: File not found: {input_file}[/red]")
        raise typer.Exit(1)
    
    # Load configuration
    config = ConfigManager.get_default_config()
    
    if config_file:
        config_path = Path(config_file)
        if config_path.exists():
            user_config = ConfigManager.load_config(config_path)
            config.update(user_config)
            if verbose:
                console.print(f"[green]Loaded config from {config_path}[/green]")
        else:
            console.print(f"[yellow]Warning: Config file not found: {config_file}[/yellow]")
    else:
        # Try to find config in standard locations
        found_config = ConfigManager.find_config()
        if found_config:
            user_config = ConfigManager.load_config(found_config)
            config.update(user_config)
            if verbose:
                console.print(f"[green]Loaded config from {found_config}[/green]")
    
    # Override config with command-line arguments
    if quality:
        config["defaults"]["quality_mode"] = quality
    if image_type:
        config["defaults"]["image_type"] = image_type
    if color_palette:
        config["defaults"]["color_palette"] = color_palette
    if denoise_strength:
        config["defaults"]["denoise_strength"] = denoise_strength
    
    # Auto-generate output path
    if output_file is None:
        output_path = input_path.with_suffix(".svg")
    else:
        output_path = Path(output_file)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if dry_run:
        console.print(Panel.fit(
            f"[bold]Dry Run[/bold]\n"
            f"Input: {input_path}\n"
            f"Output: {output_path}\n"
            f"Quality: {config['defaults']['quality_mode']}\n"
            f"Type: {config['defaults']['image_type']}\n"
            f"Colors: {config['defaults']['color_palette']}",
            title="Conversion Plan"
        ))
        return
    
    # Convert
    start_time = time.time()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Converting...", total=100)
        
        converter = Converter()
        preprocessor = Preprocessor()
        
        try:
            # Preprocessing
            if config["defaults"]["quality_mode"] != "fast":
                progress.update(task, description="Preprocessing...", completed=20)
                # TODO: Apply preprocessing pipeline from config
            
            # Conversion
            progress.update(task, description="Vectorizing...", completed=50)
            result = converter.convert(
                input_path=str(input_path),
                output_path=str(output_path),
                image_type=config["defaults"]["image_type"],
                quality_mode=config["defaults"]["quality_mode"],
            )
            
            # Optimization
            progress.update(task, description="Optimizing...", completed=80)
            # TODO: Apply output optimization from config
            
            progress.update(task, completed=100)
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)
    
    elapsed = time.time() - start_time
    
    # Display results
    if output_path.exists():
        output_size = output_path.stat().st_size
        input_size = input_path.stat().st_size
        compression = (1 - output_size / input_size) * 100 if input_size > 0 else 0
        
        table = Table(title="Conversion Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Input File", str(input_path))
        table.add_row("Output File", str(output_path))
        table.add_row("Input Size", f"{input_size / 1024:.1f} KB")
        table.add_row("Output Size", f"{output_size / 1024:.1f} KB")
        table.add_row("Compression", f"{compression:.1f}%")
        table.add_row("Time", f"{elapsed:.2f}s")
        table.add_row("Quality", config["defaults"]["quality_mode"])
        
        console.print(table)
        console.print(f"[green]✓[/green] Conversion complete: {output_path}")
    else:
        console.print("[red]Error: Output file was not created[/red]")
        raise typer.Exit(1)


@app.command()
def batch(
    input_dir: str = typer.Argument(..., help="Input directory containing images"),
    output_dir: str = typer.Option("./output", "--output", "-o", help="Output directory"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Configuration file"),
    pattern: str = typer.Option("*.{png,jpg,jpeg,bmp,tiff,gif,webp}", "--pattern", help="File pattern to match"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Process subdirectories"),
    workers: int = typer.Option(4, "--workers", "-w", help="Number of parallel workers"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Batch convert multiple images."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    if not input_path.exists():
        console.print(f"[red]Error: Directory not found: {input_dir}[/red]")
        raise typer.Exit(1)
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all matching files
    if recursive:
        files = list(input_path.rglob(pattern))
    else:
        files = list(input_path.glob(pattern))
    
    if not files:
        console.print(f"[yellow]No files found matching pattern: {pattern}[/yellow]")
        raise typer.Exit(0)
    
    console.print(f"Found {len(files)} files to convert")
    
    # Load config
    config = ConfigManager.get_default_config()
    if config_file:
        config.update(ConfigManager.load_config(Path(config_file)))
    
    # Process files
    success_count = 0
    fail_count = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Converting...", total=len(files))
        
        converter = Converter()
        
        for file in files:
            try:
                relative_path = file.relative_to(input_path)
                out_file = output_path / relative_path.with_suffix(".svg")
                out_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Skip if exists and config says to skip
                if config["batch"].get("skip_existing") and out_file.exists():
                    progress.update(task, advance=1)
                    continue
                
                result = converter.convert(
                    input_path=str(file),
                    output_path=str(out_file),
                    image_type=config["defaults"]["image_type"],
                    quality_mode=config["defaults"]["quality_mode"],
                )
                
                success_count += 1
                
            except Exception as e:
                console.print(f"[red]Failed to convert {file}: {e}[/red]")
                fail_count += 1
            
            progress.update(task, advance=1)
    
    console.print(f"\n[green]✓[/green] Completed: {success_count} succeeded, {fail_count} failed")


@app.command()
def config(
    init: bool = typer.Option(False, "--init", help="Create default config file"),
    show: bool = typer.Option(False, "--show", help="Show current config"),
    edit: bool = typer.Option(False, "--edit", help="Edit config file"),
    format: str = typer.Option("yaml", "--format", help="Config format: yaml, json"),
):
    """Manage configuration files."""
    
    if init:
        config_path = Path(".raster-to-svg.yaml")
        if config_path.exists():
            overwrite = typer.confirm("Config file already exists. Overwrite?")
            if not overwrite:
                console.print("Aborted.")
                raise typer.Exit(0)
        
        default_config = ConfigManager.get_default_config()
        ConfigManager.save_config(config_path, default_config)
        console.print(f"[green]Created config file: {config_path}[/green]")
        
        # Display the created config
        with open(config_path, 'r') as f:
            content = f.read()
        console.print(Syntax(content, "yaml"))
    
    elif show:
        found_config = ConfigManager.find_config()
        if found_config:
            config = ConfigManager.load_config(found_config)
            console.print(Panel.fit(
                Syntax(yaml.dump(config), "yaml"),
                title=f"Config from {found_config}"
            ))
        else:
            console.print("[yellow]No config file found. Using defaults.[/yellow]")
            console.print(Syntax(yaml.dump(ConfigManager.get_default_config()), "yaml"))
    
    elif edit:
        config_path = ConfigManager.find_config()
        if not config_path:
            config_path = Path(".raster-to-svg.yaml")
        
        # Open in default editor
        import subprocess
        import os
        
        editor = os.environ.get('EDITOR', 'nano')
        subprocess.call([editor, str(config_path)])
    
    else:
        console.print("Use --init to create a config, --show to display current config, or --edit to edit.")


@app.command()
def presets(
    list: bool = typer.Option(True, "--list", "-l", help="List available presets"),
    show: Optional[str] = typer.Option(None, "--show", "-s", help="Show preset details"),
    save: Optional[str] = typer.Option(None, "--save", help="Save current settings as preset"),
):
    """Manage conversion presets."""
    
    # Built-in presets
    builtin_presets = {
        "logo": {
            "description": "Optimized for logos with sharp edges",
            "quality_mode": "high",
            "image_type": "color",
            "color_palette": 64,
        },
        "photo": {
            "description": "Balanced settings for photographs",
            "quality_mode": "standard",
            "image_type": "color",
            "color_palette": 32,
        },
        "line-art": {
            "description": "Best for line drawings and sketches",
            "quality_mode": "fast",
            "image_type": "monochrome",
        },
        "document": {
            "description": "Optimized for scanned documents",
            "quality_mode": "high",
            "image_type": "monochrome",
        },
    }
    
    if list:
        table = Table(title="Available Presets")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Quality", style="green")
        table.add_column("Type", style="yellow")
        
        for name, preset in builtin_presets.items():
            table.add_row(
                name,
                preset["description"],
                preset["quality_mode"],
                preset["image_type"]
            )
        
        console.print(table)
    
    if show:
        if show in builtin_presets:
            preset = builtin_presets[show]
            console.print(Panel.fit(
                Syntax(yaml.dump(preset), "yaml"),
                title=f"Preset: {show}"
            ))
        else:
            console.print(f"[red]Preset not found: {show}[/red]")


@app.command()
def analyze(
    input_file: str = typer.Argument(..., help="Input image to analyze"),
    recommend: bool = typer.Option(True, "--recommend", "-r", help="Show recommendations"),
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed analysis"),
):
    """Analyze an image and recommend conversion settings."""
    input_path = Path(input_file)
    
    if not input_path.exists():
        console.print(f"[red]Error: File not found: {input_file}[/red]")
        raise typer.Exit(1)
    
    console.print(f"Analyzing [cyan]{input_path}[/cyan]...")
    
    # TODO: Integrate with ImageAnalyzer
    analyzer = QualityAnalyzer()
    
    try:
        recommendation = analyzer.get_recommendation(str(input_path))
        
        table = Table(title="Image Analysis Results")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        # TODO: Add more analysis results
        table.add_row("Recommended Mode", recommendation.get("recommended_mode", "standard"))
        
        console.print(table)
        
        if recommend:
            console.print(f"\n[bold]Recommendation:[/bold] Use {recommendation.get('recommended_mode', 'standard')} mode")
    
    except Exception as e:
        console.print(f"[red]Error analyzing image: {e}[/red]")


@app.command()
def watch(
    input_dir: str = typer.Argument(..., help="Directory to watch"),
    output_dir: str = typer.Option("./output", "--output", "-o", help="Output directory"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Configuration file"),
    pattern: str = typer.Option("*.{png,jpg,jpeg}", "--pattern", help="File pattern"),
):
    """Watch a directory and auto-convert new images."""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        console.print("[red]Error: watchdog package required for watch mode[/red]")
        console.print("Install with: pip install watchdog")
        raise typer.Exit(1)
    
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    if not input_path.exists():
        console.print(f"[red]Error: Directory not found: {input_dir}[/red]")
        raise typer.Exit(1)
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load config
    config = ConfigManager.get_default_config()
    if config_file:
        config.update(ConfigManager.load_config(Path(config_file)))
    
    class ImageHandler(FileSystemEventHandler):
        def on_created(self, event):
            if not event.is_directory:
                file_path = Path(event.src_path)
                if file_path.match(pattern):
                    console.print(f"[green]New file detected: {file_path.name}[/green]")
                    # TODO: Trigger conversion
    
    console.print(f"[bold]Watching {input_path} for new images...[/bold]")
    console.print("Press Ctrl+C to stop")
    
    event_handler = ImageHandler()
    observer = Observer()
    observer.schedule(event_handler, str(input_path), recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        console.print("\n[yellow]Stopped watching[/yellow]")
    
    observer.join()


if __name__ == "__main__":
    app()
