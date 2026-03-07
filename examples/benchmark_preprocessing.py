#!/usr/bin/env python
"""Example: Benchmark preprocessing performance."""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import cv2
import numpy as np
from app.services.preprocessor import Preprocessor


def benchmark_method(func, *args, **kwargs):
    """Benchmark a single method."""
    times = []
    for _ in range(3):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        times.append(elapsed)
    return result, min(times)


def main():
    """Benchmark preprocessing methods."""
    # Create test images of different sizes
    sizes = [
        ("256x256", 256, 256),
        ("512x512", 512, 512),
        ("1024x1024", 1024, 1024),
    ]

    preprocessor = Preprocessor()

    print("Preprocessing Benchmark")
    print("=" * 60)
    print()

    for size_name, width, height in sizes:
        print(f"Image size: {size_name}")
        print("-" * 60)

        # Create test image
        img = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)

        # Benchmark denoise methods
        print("  Denoise Methods:")
        
        _, t = benchmark_method(preprocessor._denoise_gaussian, img)
        print(f"    Gaussian:      {t:.3f}s")

        _, t = benchmark_method(preprocessor._denoise_bilateral, img)
        print(f"    Bilateral:     {t:.3f}s")

        if width <= 512:  # NLM is very slow for large images
            _, t = benchmark_method(preprocessor._denoise_nlm, img)
            print(f"    NLM:           {t:.3f}s")

        _, t = benchmark_method(preprocessor._denoise_median, img, kernel_size=5)
        print(f"    Median:        {t:.3f}s")

        # Benchmark contrast methods
        print("  Contrast Methods:")

        _, t = benchmark_method(preprocessor._enhance_clahe, img)
        print(f"    CLAHE:         {t:.3f}s")

        _, t = benchmark_method(preprocessor._enhance_histogram, img)
        print(f"    Histogram:     {t:.3f}s")

        # Benchmark sharpening
        print("  Sharpening:")

        _, t = benchmark_method(preprocessor._sharpen_unsharp_mask, img)
        print(f"    Unsharp Mask:  {t:.3f}s")

        # Benchmark color reduction
        print("  Color Reduction:")

        _, t = benchmark_method(preprocessor._reduce_colors_kmeans, img, max_colors=32)
        print(f"    K-means (32):  {t:.3f}s")

        _, t = benchmark_method(preprocessor._reduce_colors_median_cut, img, max_colors=32)
        print(f"    Median Cut:    {t:.3f}s")

        # Benchmark full pipelines
        print("  Full Pipelines:")

        _, t = benchmark_method(preprocessor.preprocess_array, img, "color", "fast")
        print(f"    Fast:          {t:.3f}s")

        _, t = benchmark_method(preprocessor.preprocess_array, img, "color", "standard")
        print(f"    Standard:      {t:.3f}s")

        if width <= 512:  # High mode is slow for large images
            _, t = benchmark_method(preprocessor.preprocess_array, img, "color", "high")
            print(f"    High:          {t:.3f}s")

        print()

    print("=" * 60)
    print("Benchmark complete!")


if __name__ == "__main__":
    main()
