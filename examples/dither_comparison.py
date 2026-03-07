#!/usr/bin/env python
"""Example: Compare different dithering algorithms."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import cv2
from app.services.preprocessor import Preprocessor, DitherMethod


def main():
    """Compare dithering methods."""
    if len(sys.argv) < 3:
        print("Usage: python dither_comparison.py <input_image> <output_dir>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_dir = Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Input: {input_path}")
    print(f"Output directory: {output_dir}")
    print()

    # Load image
    img = cv2.imread(input_path)
    if img is None:
        print(f"Error: Could not load image: {input_path}")
        sys.exit(1)

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cv2.imwrite(str(output_dir / "1_grayscale.png"), gray)
    print("✓ Saved grayscale")

    preprocessor = Preprocessor()

    # Simple threshold
    _, thresh = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
    cv2.imwrite(str(output_dir / "2_threshold.png"), thresh)
    print("✓ Simple threshold")

    # Otsu threshold
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cv2.imwrite(str(output_dir / "3_otsu.png"), otsu)
    print("✓ Otsu threshold")

    # Dithering methods
    print("\nApplying dithering algorithms...")
    
    floyd = preprocessor.apply_dithering(gray, DitherMethod.FLOYD_STEINBERG)
    cv2.imwrite(str(output_dir / "4_dither_floyd_steinberg.png"), floyd)
    print("  ✓ Floyd-Steinberg")

    bayer = preprocessor.apply_dithering(gray, DitherMethod.BAYER)
    cv2.imwrite(str(output_dir / "5_dither_bayer.png"), bayer)
    print("  ✓ Bayer ordered")

    atkinson = preprocessor.apply_dithering(gray, DitherMethod.ATKINSON)
    cv2.imwrite(str(output_dir / "6_dither_atkinson.png"), atkinson)
    print("  ✓ Atkinson")

    ordered = preprocessor.apply_dithering(gray, DitherMethod.ORDERED)
    cv2.imwrite(str(output_dir / "7_dither_ordered.png"), ordered)
    print("  ✓ Ordered")

    print(f"\n✓ All dithering comparisons saved to: {output_dir}")
    print("\nCompare the results to see which dithering algorithm works best for your image.")


if __name__ == "__main__":
    main()
