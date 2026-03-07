#!/usr/bin/env python
"""Example: Compare color vs monochrome conversion modes."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.converter import Converter


def main():
    """Compare color and monochrome conversion."""
    if len(sys.argv) < 2:
        print("Usage: python color_vs_bw.py <input_image>")
        sys.exit(1)

    input_path = sys.argv[1]
    base_name = Path(input_path).stem

    print(f"Input: {input_path}")
    print()

    converter = Converter()

    # Validate input
    info = converter.validate_input(input_path)
    if not info["valid"]:
        print(f"Error: {info['error']}")
        sys.exit(1)

    print(f"Original: {info['width']}x{info['height']} {info['mode']}")
    print()

    # Test auto-detection
    detected = converter._detect_image_type(input_path)
    print(f"Auto-detected type: {detected}")
    print()

    # Convert as color
    print("Converting as color image...")
    try:
        color_output = f"{base_name}_color.svg"
        color_result = converter.convert(
            input_path=input_path,
            output_path=color_output,
            image_type="color",
            quality_mode="standard",
        )
        print(f"  ✓ Color conversion: {color_output}")
        print(f"    Size: {color_result.get('output_size_bytes', 0)} bytes")
        print(f"    Time: {color_result['processing_time']:.2f}s")
    except Exception as e:
        print(f"  ✗ Color conversion failed: {e}")

    print()

    # Convert as monochrome
    print("Converting as monochrome image...")
    try:
        bw_output = f"{base_name}_bw.svg"
        bw_result = converter.convert(
            input_path=input_path,
            output_path=bw_output,
            image_type="monochrome",
            quality_mode="standard",
        )
        print(f"  ✓ Monochrome conversion: {bw_output}")
        print(f"    Size: {bw_result.get('output_size_bytes', 0)} bytes")
        print(f"    Time: {bw_result['processing_time']:.2f}s")
    except Exception as e:
        print(f"  ✗ Monochrome conversion failed: {e}")

    print()
    print("Comparison complete!")


if __name__ == "__main__":
    main()
