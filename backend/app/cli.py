"""Command-line interface for raster-to-SVG conversion."""

import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.services.converter import Converter
from app.services.preprocessor import Preprocessor
from app.services.quality_analyzer import QualityAnalyzer

app = typer.Typer(
    name="raster-to-svg",
    help="Convert raster images to vector SVG format",
    no_args_is_help=True,
)
console = Console()


@app.command()
def convert(
    input_file: str = typer.Argument(..., help="Input raster image path"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Output SVG file path"),
    image_type: str = typer.Option(
        "auto", "--type", "-t", help="Image type: auto, color, monochrome"
    ),
    quality: str = typer.Option(
        "standard", "--quality", "-q", help="Quality mode: fast, standard, high"
    ),
    color_palette: int = typer.Option(
        32, "--colors", "-c", help="Maximum colors for color reduction (8-256)"
    ),
    denoise_strength: str = typer.Option(
        "medium", "--denoise", "-d", help="Denoise strength: light, medium, heavy"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    show_preprocessing: bool = typer.Option(
        False, "--show-preprocessing", "-s", help="Show preprocessing steps"
    ),
):
    """Convert a single raster image to SVG."""
    input_path = Path(input_file)

    # Validate input
    if not input_path.exists():
        console.print(f"[red]Error: File not found: {input_file}[/red]")
        raise typer.Exit(1)

    # Auto-generate output path if not provided
    if output_file is None:
        output_path = input_path.with_suffix(".svg")
    else:
        output_path = Path(output_file)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Validate image type
    if image_type not in ["auto", "color", "monochrome"]:
        console.print(f"[red]Error: Invalid image type: {image_type}[/red]")
        raise typer.Exit(1)

    # Validate quality mode
    if quality not in ["fast", "standard", "high"]:
        console.print(f"[red]Error: Invalid quality mode: {quality}[/red]")
        raise typer.Exit(1)

    # Convert
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Converting image...", total=None)

        converter = Converter()

        try:
            # Update preprocessor settings if needed
            if quality != "fast":
                # TODO: Pass preprocessing options to converter
                pass

            result = converter.convert(
                input_path=str(input_path),
                output_path=str(output_path),
                image_type=image_type,
                quality_mode=quality,
            )

            progress.update(task, completed=True)

            # Display results
            console.print(f"\n[green]✓ Conversion successful![/green]")
            console.print(f"  Input:  {input_path}")
            console.print(f"  Output: {output_path}")
            console.print(f"  Time:   {result['processing_time']:.2f}s")
            console.print(f"  Engine: {result.get('engine', 'unknown')}")

            if show_preprocessing and quality != "fast":
                console.print(f"\n[cyan]Preprocessing applied:[/cyan]")
                for step in result.get("preprocessing_applied", []):
                    console.print(f"  • {step}")

            if verbose:
                console.print(f"\n[cyan]Details:[/cyan]")
                console.print(f"  Image type: {result['image_type']}")
                console.print(f"  Quality mode: {result['quality_mode']}")
                console.print(f"  Original size: {result.get('file_size_bytes', 0)} bytes")
                console.print(f"  Output size: {result.get('output_size_bytes', 0)} bytes")
                if "compression_ratio" in result:
                    console.print(f"  Compression ratio: {result['compression_ratio']:.2f}x")
                if result.get("optimization_applied"):
                    console.print(f"  Optimization: {result['optimization_level']}")

        except FileNotFoundError as e:
            progress.update(task, completed=True)
            console.print(f"[red]✗ File not found: {e}[/red]")
            raise typer.Exit(1)
        except ValueError as e:
            progress.update(task, completed=True)
            console.print(f"[red]✗ Invalid input: {e}[/red]")
            raise typer.Exit(1)
        except RuntimeError as e:
            progress.update(task, completed=True)
            console.print(f"[red]✗ Conversion failed: {e}[/red]")
            raise typer.Exit(1)
        except Exception as e:
            progress.update(task, completed=True)
            console.print(f"[red]✗ Unexpected error: {e}[/red]")
            if verbose:
                import traceback

                console.print(traceback.format_exc())
            raise typer.Exit(1)


@app.command()
def batch(
    input_dir: str = typer.Argument(..., help="Input directory containing images"),
    output_dir: str = typer.Option(..., "--output", "-o", help="Output directory for SVGs"),
    pattern: str = typer.Option("*.png", "--pattern", "-p", help="File glob pattern"),
    quality: str = typer.Option("standard", "--quality", "-q", help="Quality mode"),
):
    """Batch convert directory of images."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    if not input_path.exists():
        console.print(f"[red]Error: Directory not found: {input_dir}[/red]")
        raise typer.Exit(1)

    output_path.mkdir(parents=True, exist_ok=True)

    # Find matching files
    files = list(input_path.glob(pattern))
    if not files:
        console.print(f"[yellow]No files matching pattern: {pattern}[/yellow]")
        raise typer.Exit(0)

    console.print(f"Found {len(files)} files to convert")
    console.print(f"Quality mode: {quality}")
    console.print()

    converter = Converter()
    success_count = 0
    fail_count = 0

    for file in files:
        out_file = output_path / file.with_suffix(".svg").name
        console.print(f"Converting {file.name}...", end=" ")
        try:
            converter.convert(
                input_path=str(file),
                output_path=str(out_file),
                quality_mode=quality,
            )
            console.print("[green]✓[/green]")
            success_count += 1
        except Exception as e:
            console.print(f"[red]✗ ({e})[/red]")
            fail_count += 1

    console.print(f"\nComplete: {success_count} succeeded, {fail_count} failed")


@app.command()
def preprocess(
    input_file: str = typer.Argument(..., help="Input image path"),
    output_dir: str = typer.Option(
        ..., "--output", "-o", help="Output directory for processed images"
    ),
    quality: str = typer.Option(
        "standard", "--quality", "-q", help="Quality mode: fast, standard, high"
    ),
    compare: bool = typer.Option(
        False, "--compare", "-c", help="Generate comparison of all preprocessing methods"
    ),
):
    """Apply preprocessing to an image without converting to SVG."""
    input_path = Path(input_file)
    output_path = Path(output_dir)

    if not input_path.exists():
        console.print(f"[red]Error: File not found: {input_file}[/red]")
        raise typer.Exit(1)

    output_path.mkdir(parents=True, exist_ok=True)
    preprocessor = Preprocessor()

    if compare:
        # Generate comparison of all methods
        console.print("Generating preprocessing comparison...")

        methods = ["original", "gaussian", "bilateral", "nlm", "clahe", "sharpen", "kmeans"]
        results = preprocessor.compare_methods(str(input_path), str(output_path), methods)

        console.print(f"\n[green]✓ Comparison complete![/green]")
        console.print(f"Results saved to: {output_path}")
        for method, file_path in results.items():
            console.print(f"  • {method}: {file_path}")
    else:
        # Apply selected quality mode preprocessing
        console.print(f"Applying {quality} preprocessing...")

        import cv2

        img = cv2.imread(str(input_path))

        # Detect image type
        is_color = len(img.shape) == 3
        image_type = "color" if is_color else "monochrome"

        # Apply preprocessing
        result = preprocessor.preprocess_array(img, image_type, quality)

        # Save result
        output_file = output_path / f"{input_path.stem}_{quality}.png"
        cv2.imwrite(str(output_file), result)

        console.print(f"\n[green]✓ Preprocessing complete![/green]")
        console.print(f"  Input:  {input_path}")
        console.print(f"  Output: {output_file}")

        if quality == "standard":
            console.print(f"\n[cyan]Applied:[/cyan]")
            console.print("  • Color reduction")
            console.print("  • Bilateral denoising")
            console.print("  • CLAHE contrast enhancement")
        elif quality == "high":
            console.print(f"\n[cyan]Applied:[/cyan]")
            console.print("  • Color reduction")
            console.print("  • Non-Local Means denoising")
            console.print("  • CLAHE contrast enhancement")
            console.print("  • Unsharp mask sharpening")
            console.print("  • Edge enhancement")


@app.command()
def compare(
    input_file: str = typer.Argument(..., help="Input image path"),
    output_dir: str = typer.Option(..., "--output", "-o", help="Output directory for results"),
):
    """Compare all three quality modes on the same image."""
    input_path = Path(input_file)
    output_path = Path(output_dir)

    if not input_path.exists():
        console.print(f"[red]Error: File not found: {input_file}[/red]")
        raise typer.Exit(1)

    output_path.mkdir(parents=True, exist_ok=True)

    console.print(f"Comparing quality modes for: {input_file}")
    console.print()

    converter = Converter()
    results = {}

    for quality in ["fast", "standard", "high"]:
        out_file = output_path / f"{input_path.stem}_{quality}.svg"
        console.print(f"Converting with {quality} mode...", end=" ")

        try:
            start = time.time()
            result = converter.convert(
                input_path=str(input_path),
                output_path=str(out_file),
                quality_mode=quality,
            )
            elapsed = time.time() - start

            results[quality] = {
                "time": elapsed,
                "output_size": result.get("output_size_bytes", 0),
                "success": True,
            }
            console.print(f"[green]✓[/green] ({elapsed:.2f}s)")
        except Exception as e:
            results[quality] = {"error": str(e), "success": False}
            console.print(f"[red]✗ ({e})[/red]")

    # Display comparison table
    console.print()
    table = Table(title="Quality Mode Comparison")
    table.add_column("Mode", style="cyan")
    table.add_column("Time", style="green")
    table.add_column("Output Size", style="blue")
    table.add_column("Status", style="magenta")

    for quality, result in results.items():
        if result.get("success"):
            table.add_row(
                quality.capitalize(),
                f"{result['time']:.2f}s",
                f"{result['output_size']:,} bytes",
                "✓ Success",
            )
        else:
            table.add_row(quality.capitalize(), "-", "-", f"✗ {result.get('error', 'Failed')}")

    console.print(table)
    console.print(f"\n[green]✓ Comparison complete![/green]")
    console.print(f"Results saved to: {output_path}")


@app.command()
def recommend(
    input_file: str = typer.Argument(..., help="Image file to analyze"),
):
    """Analyze image and recommend optimal quality mode."""
    input_path = Path(input_file)

    if not input_path.exists():
        console.print(f"[red]Error: File not found: {input_file}[/red]")
        raise typer.Exit(1)

    console.print(f"Analyzing: {input_file}...")

    analyzer = QualityAnalyzer()
    recommendation = analyzer.get_recommendation(str(input_path))

    if "error" in recommendation:
        console.print(f"[red]Error: {recommendation['error']}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[cyan]Recommendation:[/cyan]")
    console.print(f"  Mode: [green]{recommendation['recommended_mode']}[/green]")
    console.print(f"  Reason: {recommendation['reason']}")

    console.print(f"\n[cyan]Image Characteristics:[/cyan]")
    for key, value in recommendation["characteristics"].items():
        console.print(f"  • {key}: {value}")


@app.command()
def info():
    """Show tool information and version."""
    table = Table(title="Raster to SVG Converter")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Name", settings.APP_NAME)
    table.add_row("Version", settings.APP_VERSION)
    table.add_row("API Host", settings.API_HOST)
    table.add_row("API Port", str(settings.API_PORT))
    table.add_row("Debug Mode", str(settings.DEBUG))

    console.print(table)

    # Check engine availability
    converter = Converter()
    engine_info = converter.get_engine_info()

    console.print("\n[cyan]Conversion Engines:[/cyan]")
    for engine, info in engine_info.items():
        status = "[green]✓[/green]" if info["available"] else "[red]✗[/red]"
        console.print(f"  {status} {engine}")

    console.print("\n[cyan]Supported Input Formats:[/cyan]")
    console.print("  PNG, JPG, JPEG, BMP, TIFF, GIF, WEBP")

    console.print("\n[cyan]Supported Output Formats:[/cyan]")
    console.print("  SVG")

    console.print("\n[cyan]Quality Modes:[/cyan]")
    console.print("  fast     - Direct conversion, no preprocessing")
    console.print("  standard - Color reduction + denoise + CLAHE")
    console.print("  high     - Standard + sharpening + edge enhancement")

    console.print("\n[cyan]Preprocessing Methods:[/cyan]")
    console.print("  Color Reduction  - K-means clustering (8-256 colors)")
    console.print("  Denoise          - Gaussian, Bilateral, NLM, Median")
    console.print("  Contrast         - CLAHE, Histogram, Levels, Sigmoid")
    console.print("  Sharpen          - Unsharp mask, Kernel-based")
    console.print("  Edge Enhancement - Laplacian, Sobel, Scharr")
    console.print("  Dithering        - Floyd-Steinberg, Bayer, Atkinson")


@app.command()
def validate(
    input_file: str = typer.Argument(..., help="Image file to validate"),
):
    """Validate an image file and show its properties."""
    input_path = Path(input_file)

    if not input_path.exists():
        console.print(f"[red]Error: File not found: {input_file}[/red]")
        raise typer.Exit(1)

    converter = Converter()
    info = converter.validate_input(input_file)

    if not info["valid"]:
        console.print(f"[red]Invalid image: {info['error']}[/red]")
        raise typer.Exit(1)

    table = Table(title=f"Image Properties: {input_path.name}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Format", info.get("format", "Unknown"))
    table.add_row("Mode", info.get("mode", "Unknown"))
    table.add_row("Dimensions", f"{info['width']} x {info['height']}")
    table.add_row("Size", f"{info['file_size']:,} bytes ({info['file_size'] / 1024:.1f} KB)")

    # Detect image type
    detected_type = converter._detect_image_type(input_file)
    table.add_row("Detected Type", detected_type)

    # Estimate preprocessing time
    if info["width"] * info["height"] < 1000000:  # < 1MP
        est_time = "< 1s"
    elif info["width"] * info["height"] < 5000000:  # < 5MP
        est_time = "1-3s"
    else:
        est_time = "3-10s"
    table.add_row("Est. Fast Mode", est_time)
    table.add_row("Est. Standard Mode", f"{est_time} + preprocessing")
    table.add_row("Est. High Mode", f"{est_time} + heavy preprocessing")

    console.print(table)


@app.command()
def dither(
    input_file: str = typer.Argument(..., help="Input image path"),
    output_file: str = typer.Option(..., "--output", "-o", help="Output image path"),
    method: str = typer.Option(
        "floyd-steinberg",
        "--method",
        "-m",
        help="Dithering method: floyd-steinberg, bayer, atkinson, ordered",
    ),
):
    """Apply dithering to convert image to black and white."""
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        console.print(f"[red]Error: File not found: {input_file}[/red]")
        raise typer.Exit(1)

    preprocessor = Preprocessor()

    import cv2

    img = cv2.imread(str(input_path))

    # Map method string to enum
    method_map = {
        "floyd-steinberg": preprocessor.DitherMethod.FLOYD_STEINBERG,
        "bayer": preprocessor.DitherMethod.BAYER,
        "atkinson": preprocessor.DitherMethod.ATKINSON,
        "ordered": preprocessor.DitherMethod.ORDERED,
    }

    if method not in method_map:
        console.print(f"[red]Error: Unknown method: {method}[/red]")
        raise typer.Exit(1)

    # Apply dithering
    result = preprocessor.apply_dithering(img, method_map[method])

    # Save result
    cv2.imwrite(str(output_path), result)

    console.print(f"[green]✓ Dithering complete![/green]")
    console.print(f"  Method: {method}")
    console.print(f"  Input:  {input_path}")
    console.print(f"  Output: {output_path}")


if __name__ == "__main__":
    app()
