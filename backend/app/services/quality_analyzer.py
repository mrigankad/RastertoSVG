"""Quality analysis service for comparing conversion results."""

import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image
from skimage import metrics

logger = logging.getLogger(__name__)


class QualityAnalyzer:
    """
    Analyze and compare conversion quality.
    
    Provides metrics for:
    - Edge preservation
    - Color accuracy
    - File size efficiency
    - Visual similarity
    """

    def __init__(self):
        pass

    def compare_conversions(
        self,
        original_path: str,
        svg_paths: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Compare multiple SVG outputs from the same original image.
        
        Args:
            original_path: Path to original raster image
            svg_paths: Dictionary mapping quality mode to SVG path
            
        Returns:
            Comparison results with metrics for each mode
        """
        # Load original image
        original = cv2.imread(original_path)
        if original is None:
            raise ValueError(f"Could not load original image: {original_path}")
        
        results = {}
        
        for mode, svg_path in svg_paths.items():
            try:
                # Render SVG to raster for comparison
                rendered = self._render_svg(svg_path, original.shape[:2])
                
                # Calculate metrics
                metrics_dict = self._calculate_metrics(original, rendered)
                
                # Get file size
                file_size = Path(svg_path).stat().st_size
                
                results[mode] = {
                    "file_size_bytes": file_size,
                    "file_size_kb": round(file_size / 1024, 2),
                    "metrics": metrics_dict,
                }
            except Exception as e:
                logger.error(f"Failed to analyze {mode}: {e}")
                results[mode] = {"error": str(e)}
        
        return {
            "original": {
                "path": original_path,
                "size": original.shape,
                "file_size_bytes": Path(original_path).stat().st_size,
            },
            "comparisons": results,
        }

    def _render_svg(self, svg_path: str, target_size: Tuple[int, int]) -> np.ndarray:
        """Render SVG to raster image for comparison."""
        # Use cairosvg or similar for rendering
        # For now, return a placeholder
        try:
            import cairosvg
            
            # Render to PNG
            png_data = cairosvg.svg2png(
                url=svg_path,
                output_width=target_size[1],
                output_height=target_size[0],
            )
            
            # Convert to OpenCV format
            nparr = np.frombuffer(png_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            return img
        except ImportError:
            logger.warning("cairosvg not available, using placeholder")
            return np.zeros((*target_size, 3), dtype=np.uint8)
        except Exception as e:
            logger.error(f"SVG rendering failed: {e}")
            return np.zeros((*target_size, 3), dtype=np.uint8)

    def _calculate_metrics(
        self,
        original: np.ndarray,
        converted: np.ndarray,
    ) -> Dict[str, float]:
        """Calculate quality metrics between two images."""
        # Ensure same size
        if original.shape != converted.shape:
            converted = cv2.resize(converted, (original.shape[1], original.shape[0]))
        
        # Convert to grayscale for structural metrics
        original_gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
        converted_gray = cv2.cvtColor(converted, cv2.COLOR_BGR2GRAY)
        
        metrics_dict = {}
        
        # SSIM (Structural Similarity)
        try:
            ssim = metrics.structural_similarity(
                original_gray,
                converted_gray,
                data_range=255,
            )
            metrics_dict["ssim"] = round(ssim, 4)
        except Exception as e:
            logger.warning(f"SSIM calculation failed: {e}")
            metrics_dict["ssim"] = 0.0
        
        # MSE (Mean Squared Error)
        mse = np.mean((original.astype(float) - converted.astype(float)) ** 2)
        metrics_dict["mse"] = round(mse, 2)
        
        # PSNR (Peak Signal-to-Noise Ratio)
        if mse == 0:
            psnr = float('inf')
        else:
            psnr = 20 * np.log10(255.0 / np.sqrt(mse))
        metrics_dict["psnr"] = round(psnr, 2) if psnr != float('inf') else 99.99
        
        # Histogram correlation
        hist_corr = self._histogram_correlation(original, converted)
        metrics_dict["histogram_correlation"] = round(hist_corr, 4)
        
        # Edge preservation
        edge_score = self._edge_preservation_score(original, converted)
        metrics_dict["edge_preservation"] = round(edge_score, 4)
        
        return metrics_dict

    def _histogram_correlation(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """Calculate histogram correlation between two images."""
        hist1 = cv2.calcHist([img1], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([img2], [0], None, [256], [0, 256])
        
        # Normalize
        hist1 = cv2.normalize(hist1, hist1).flatten()
        hist2 = cv2.normalize(hist2, hist2).flatten()
        
        # Correlation
        correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        
        return correlation

    def _edge_preservation_score(self, original: np.ndarray, converted: np.ndarray) -> float:
        """Calculate edge preservation score."""
        # Detect edges in both images
        orig_gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
        conv_gray = cv2.cvtColor(converted, cv2.COLOR_BGR2GRAY)
        
        orig_edges = cv2.Canny(orig_gray, 50, 150)
        conv_edges = cv2.Canny(conv_gray, 50, 150)
        
        # Calculate overlap
        intersection = np.logical_and(orig_edges > 0, conv_edges > 0).sum()
        union = np.logical_or(orig_edges > 0, conv_edges > 0).sum()
        
        if union == 0:
            return 1.0
        
        iou = intersection / union
        return iou

    def analyze_svg_complexity(self, svg_path: str) -> Dict[str, Any]:
        """Analyze SVG file complexity."""
        try:
            with open(svg_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Count elements
            import re
            
            path_count = len(re.findall(r'<path', content))
            circle_count = len(re.findall(r'<circle', content))
            rect_count = len(re.findall(r'<rect', content))
            polygon_count = len(re.findall(r'<polygon', content))
            
            # Count path commands
            path_data = ' '.join(re.findall(r'd="([^"]*)"', content))
            commands = re.findall(r'[MmLlHhVvCcSsQqTtAaZz]', path_data)
            
            # Estimate node count
            numbers = re.findall(r'-?\d+\.?\d*', path_data)
            
            return {
                "file_size_bytes": len(content.encode('utf-8')),
                "element_counts": {
                    "paths": path_count,
                    "circles": circle_count,
                    "rects": rect_count,
                    "polygons": polygon_count,
                },
                "total_elements": path_count + circle_count + rect_count + polygon_count,
                "path_commands": len(commands),
                "estimated_nodes": len(numbers) // 2,
            }
        except Exception as e:
            logger.error(f"SVG analysis failed: {e}")
            return {"error": str(e)}

    def generate_comparison_report(
        self,
        original_path: str,
        svg_paths: Dict[str, str],
        output_path: str,
    ) -> str:
        """Generate HTML comparison report."""
        comparison = self.compare_conversions(original_path, svg_paths)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Conversion Quality Report</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1, h2 {{ color: #333; }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 20px 0;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 12px;
                    text-align: left;
                }}
                th {{
                    background-color: #4CAF50;
                    color: white;
                }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .metric-good {{ color: green; }}
                .metric-medium {{ color: orange; }}
                .metric-bad {{ color: red; }}
                .image-comparison {{
                    display: flex;
                    gap: 20px;
                    margin: 20px 0;
                }}
                .image-comparison img {{
                    max-width: 300px;
                    border: 1px solid #ddd;
                }}
            </style>
        </head>
        <body>
            <h1>Conversion Quality Report</h1>
            
            <h2>Original Image</h2>
            <p>Path: {comparison['original']['path']}</p>
            <p>Size: {comparison['original']['size']}</p>
            <p>File Size: {comparison['original']['file_size_bytes']:,} bytes</p>
            
            <h2>Comparison Metrics</h2>
            <table>
                <tr>
                    <th>Mode</th>
                    <th>File Size (KB)</th>
                    <th>SSIM</th>
                    <th>MSE</th>
                    <th>PSNR</th>
                    <th>Edge Preservation</th>
                </tr>
        """
        
        for mode, data in comparison['comparisons'].items():
            if 'error' in data:
                html += f"""
                <tr>
                    <td>{mode}</td>
                    <td colspan="6" style="color: red;">Error: {data['error']}</td>
                </tr>
                """
            else:
                metrics = data['metrics']
                html += f"""
                <tr>
                    <td><strong>{mode}</strong></td>
                    <td>{data['file_size_kb']}</td>
                    <td>{metrics.get('ssim', 'N/A')}</td>
                    <td>{metrics.get('mse', 'N/A')}</td>
                    <td>{metrics.get('psnr', 'N/A')}</td>
                    <td>{metrics.get('edge_preservation', 'N/A')}</td>
                </tr>
                """
        
        html += """
            </table>
            
            <h2>Recommendations</h2>
            <ul>
                <li><strong>Fast Mode:</strong> Best for simple graphics, fastest processing</li>
                <li><strong>Standard Mode:</strong> Best balance of quality and speed for most images</li>
                <li><strong>High Mode:</strong> Best quality for complex images and professional work</li>
            </ul>
        </body>
        </html>
        """
        
        # Save report
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_path

    def get_recommendation(self, image_path: str) -> Dict[str, str]:
        """Get quality mode recommendation based on image analysis."""
        img = cv2.imread(image_path)
        if img is None:
            return {"error": "Could not load image"}
        
        # Analyze image characteristics
        height, width = img.shape[:2]
        pixel_count = height * width
        
        # Calculate color variation
        if len(img.shape) == 3:
            std = np.std(img)
            unique_colors = len(np.unique(img.reshape(-1, 3), axis=0))
        else:
            std = np.std(img)
            unique_colors = len(np.unique(img))
        
        # Edge density
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.count_nonzero(edges) / edges.size
        
        # Make recommendation
        if unique_colors < 50 and edge_density < 0.05:
            recommendation = "fast"
            reason = "Simple image with few colors and low detail"
        elif pixel_count > 2000000 or unique_colors > 10000:
            recommendation = "high"
            reason = "Complex image with high resolution or many colors"
        else:
            recommendation = "standard"
            reason = "Balanced image suitable for standard processing"
        
        return {
            "recommended_mode": recommendation,
            "reason": reason,
            "characteristics": {
                "resolution": f"{width}x{height}",
                "unique_colors": int(unique_colors),
                "edge_density": round(edge_density, 4),
                "color_variation": round(float(std), 2),
            },
        }
