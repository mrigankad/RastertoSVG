#!/usr/bin/env python
"""Example: Convert a single image to SVG."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.converter import Converter


def main():
    """Convert a single image."""
    if len(sys.argv) < 2:
        print("Usage: python convert_single.py <input_image> [output.svg]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else input_path.rsplit(".", 1)[0] + ".svg"

    print(f"Converting: {input_path}")
    print(f"Output: {output_path}")

    converter = Converter()

    # Validate input
    info = converter.validate_input(input_path)
    if not info["valid"]:
        print(f"Error: {info['error']}")
        sys.exit(1)

    print(f"Image info: {info}")

    # Convert
    try:
        result = converter.convert(
            input_path=input_path,
            output_path=output_path,
            image_type="auto",
            quality_mode="standard",
        )

        print(f"\nConversion successful!")
        print(f"  Engine: {result.get('engine', 'unknown')}")
        print(f"  Image type: {result['image_type']}")
        print(f"  Quality mode: {result['quality_mode']}")
        print(f"  Processing time: {result['processing_time']:.2f}s")
        print(f"  Output size: {result.get('output_size_bytes', 0)} bytes")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
