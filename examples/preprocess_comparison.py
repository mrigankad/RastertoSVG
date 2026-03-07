#!/usr/bin/env python
"""Example: Compare different preprocessing methods."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import cv2
from app.services.preprocessor import Preprocessor, DenoiseMethod, ContrastMethod


def main():
    """Compare preprocessing methods."""
    if len(sys.argv) < 3:
        print("Usage: python preprocess_comparison.py <input_image> <output_dir>")
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

    print(f"Image size: {img.shape}")
    print()

    preprocessor = Preprocessor()

    # Save original
    cv2.imwrite(str(output_dir / "1_original.png"), img)
    print("✓ Saved original")

    # Denoise methods
    print("\nApplying denoise methods...")
    
    gaussian = preprocessor._denoise_gaussian(img, kernel_size=5, sigma=1.0)
    cv2.imwrite(str(output_dir / "2_denoise_gaussian.png"), gaussian)
    print("  ✓ Gaussian denoise")

    bilateral = preprocessor._denoise_bilateral(img, d=9, sigma_color=75, sigma_space=75)
    cv2.imwrite(str(output_dir / "3_denoise_bilateral.png"), bilateral)
    print("  ✓ Bilateral denoise")

    nlm = preprocessor._denoise_nlm(img, h=10)
    cv2.imwrite(str(output_dir / "4_denoise_nlm.png"), nlm)
    print("  ✓ Non-Local Means denoise")

    # Contrast enhancement
    print("\nApplying contrast enhancement...")
    
    clahe = preprocessor._enhance_clahe(img, clip_limit=2.0)
    cv2.imwrite(str(output_dir / "5_contrast_clahe.png"), clahe)
    print("  ✓ CLAHE contrast")

    histogram = preprocessor._enhance_histogram(img)
    cv2.imwrite(str(output_dir / "6_contrast_histogram.png"), histogram)
    print("  ✓ Histogram equalization")

    # Sharpening
    print("\nApplying sharpening...")
    
    sharpened = preprocessor._sharpen_unsharp_mask(img, kernel_size=5, sigma=1.0, amount=1.5)
    cv2.imwrite(str(output_dir / "7_sharpen_unsharp.png"), sharpened)
    print("  ✓ Unsharp mask")

    # Edge enhancement
    print("\nApplying edge enhancement...")
    
    edges_lap = preprocessor._enhance_edges(img, method="laplacian")
    cv2.imwrite(str(output_dir / "8_edges_laplacian.png"), edges_lap)
    print("  ✓ Laplacian edges")

    edges_sobel = preprocessor._enhance_edges(img, method="sobel")
    cv2.imwrite(str(output_dir / "9_edges_sobel.png"), edges_sobel)
    print("  ✓ Sobel edges")

    # Color reduction
    if len(img.shape) == 3:
        print("\nApplying color reduction...")
        
        reduced_16 = preprocessor._reduce_colors_kmeans(img, max_colors=16)
        cv2.imwrite(str(output_dir / "10_colors_16.png"), reduced_16)
        print("  ✓ 16 colors (k-means)")

        reduced_32 = preprocessor._reduce_colors_kmeans(img, max_colors=32)
        cv2.imwrite(str(output_dir / "11_colors_32.png"), reduced_32)
        print("  ✓ 32 colors (k-means)")

    # Full pipelines
    print("\nApplying full preprocessing pipelines...")
    
    standard = preprocessor.preprocess_array(img, "color", "standard")
    cv2.imwrite(str(output_dir / "12_pipeline_standard.png"), standard)
    print("  ✓ Standard pipeline")

    high = preprocessor.preprocess_array(img, "color", "high")
    cv2.imwrite(str(output_dir / "13_pipeline_high.png"), high)
    print("  ✓ High quality pipeline")

    print(f"\n✓ All comparisons saved to: {output_dir}")


if __name__ == "__main__":
    main()
