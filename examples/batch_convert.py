#!/usr/bin/env python
"""Example: Batch convert images in a directory."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.converter import Converter


def main():
    """Batch convert images."""
    if len(sys.argv) < 3:
        print("Usage: python batch_convert.py <input_dir> <output_dir> [quality]")
        print("  quality: fast, standard, or high (default: standard)")
        sys.exit(1)

    input_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    quality = sys.argv[3] if len(sys.argv) > 3 else "standard"

    if not input_dir.exists():
        print(f"Error: Input directory not found: {input_dir}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all images
    extensions = [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"]
    images = [f for f in input_dir.iterdir() if f.suffix.lower() in extensions]

    if not images:
        print(f"No images found in {input_dir}")
        sys.exit(0)

    print(f"Found {len(images)} images to convert")
    print(f"Quality mode: {quality}")
    print()

    converter = Converter()
    success_count = 0
    fail_count = 0

    for i, img_path in enumerate(images, 1):
        output_path = output_dir / f"{img_path.stem}.svg"
        print(f"[{i}/{len(images)}] Converting: {img_path.name}...", end=" ")

        try:
            result = converter.convert(
                input_path=str(img_path),
                output_path=str(output_path),
                image_type="auto",
                quality_mode=quality,
            )
            print(f"✓ ({result['processing_time']:.2f}s)")
            success_count += 1

        except Exception as e:
            print(f"✗ ({e})")
            fail_count += 1

    print()
    print(f"Complete: {success_count} succeeded, {fail_count} failed")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
