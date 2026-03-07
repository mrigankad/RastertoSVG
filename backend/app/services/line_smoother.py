"""Line smoothing service for SVG path optimization."""

import logging
import re
from typing import List, Literal, Optional, Tuple

import numpy as np
from scipy import interpolate

logger = logging.getLogger(__name__)


class LineSmoother:
    """
    Line smoothing service for optimizing SVG paths.
    
    Provides algorithms for smoothing and simplifying vector paths:
    - Catmull-Rom splines for smooth curves
    - Bezier curve fitting
    - Ramer-Douglas-Peucker simplification
    - Adaptive smoothing based on path complexity
    """

    def __init__(self):
        self.methods = {
            "catmull-rom": self.catmull_rom_spline,
            "bezier": self.bezier_smoothing,
            "rdp": self.rdp_simplification,
            "adaptive": self.adaptive_smoothing,
        }

    def smooth_points(
        self,
        points: List[Tuple[float, float]],
        method: Literal["catmull-rom", "bezier", "rdp", "adaptive"] = "catmull-rom",
        **kwargs
    ) -> List[Tuple[float, float]]:
        """
        Smooth a list of 2D points.
        
        Args:
            points: List of (x, y) coordinate tuples
            method: Smoothing algorithm
            **kwargs: Additional parameters for specific methods
            
        Returns:
            List of smoothed points
        """
        if len(points) < 2:
            return points
        
        if method not in self.methods:
            raise ValueError(f"Unknown smoothing method: {method}")
        
        return self.methods[method](points, **kwargs)

    def catmull_rom_spline(
        self,
        points: List[Tuple[float, float]],
        tension: float = 0.5,
        num_points: int = 100,
    ) -> List[Tuple[float, float]]:
        """
        Create smooth curve using Catmull-Rom spline.
        
        Args:
            points: Control points
            tension: Curve tension (0-1)
            num_points: Number of output points
            
        Returns:
            Smoothed points
        """
        if len(points) < 2:
            return points
        
        # Convert to numpy arrays
        points = np.array(points)
        
        # Add phantom points at start and end
        if len(points) == 2:
            # Linear interpolation for 2 points
            t = np.linspace(0, 1, num_points)
            result = []
            for ti in t:
                x = points[0, 0] * (1 - ti) + points[1, 0] * ti
                y = points[0, 1] * (1 - ti) + points[1, 1] * ti
                result.append((x, y))
            return result
        
        # For more points, use interpolation
        try:
            # Parametric interpolation
            t = np.linspace(0, 1, len(points))
            t_new = np.linspace(0, 1, num_points)
            
            # Fit spline for x and y separately
            cs_x = interpolate.CubicSpline(t, points[:, 0])
            cs_y = interpolate.CubicSpline(t, points[:, 1])
            
            x_new = cs_x(t_new)
            y_new = cs_y(t_new)
            
            return list(zip(x_new, y_new))
        except Exception as e:
            logger.warning(f"Catmull-Rom spline failed: {e}, returning original points")
            return list(map(tuple, points))

    def bezier_smoothing(
        self,
        points: List[Tuple[float, float]],
        degree: int = 3,
        num_points: int = 100,
    ) -> List[Tuple[float, float]]:
        """
        Smooth using Bezier curve approximation.
        
        Args:
            points: Control points
            degree: Bezier curve degree
            num_points: Number of output points
            
        Returns:
            Smoothed points
        """
        if len(points) < 2:
            return points
        
        points = np.array(points)
        
        try:
            # Use B-spline for smoothing
            t = np.linspace(0, 1, len(points))
            t_new = np.linspace(0, 1, num_points)
            
            # Fit B-spline
            tck, u = interpolate.splprep([points[:, 0], points[:, 1]], s=len(points))
            out = interpolate.splev(t_new, tck)
            
            return list(zip(out[0], out[1]))
        except Exception as e:
            logger.warning(f"Bezier smoothing failed: {e}, returning original points")
            return list(map(tuple, points))

    def rdp_simplification(
        self,
        points: List[Tuple[float, float]],
        epsilon: float = 1.0,
    ) -> List[Tuple[float, float]]:
        """
        Ramer-Douglas-Peucker simplification.
        
        Reduces the number of points while preserving shape.
        
        Args:
            points: Input points
            epsilon: Distance threshold (higher = more simplification)
            
        Returns:
            Simplified points
        """
        if len(points) <= 2:
            return points
        
        def point_line_distance(point, start, end):
            """Calculate perpendicular distance from point to line."""
            if np.all(start == end):
                return np.linalg.norm(point - start)
            
            return np.abs(np.cross(end - start, start - point)) / np.linalg.norm(end - start)
        
        def rdp_recursive(points, epsilon, start_idx, end_idx, result):
            """Recursive RDP implementation."""
            if end_idx <= start_idx + 1:
                return
            
            # Find point with maximum distance
            start_point = np.array(points[start_idx])
            end_point = np.array(points[end_idx])
            
            max_dist = 0
            max_idx = start_idx
            
            for i in range(start_idx + 1, end_idx):
                dist = point_line_distance(np.array(points[i]), start_point, end_point)
                if dist > max_dist:
                    max_dist = dist
                    max_idx = i
            
            # If max distance is greater than epsilon, recursively simplify
            if max_dist > epsilon:
                rdp_recursive(points, epsilon, start_idx, max_idx, result)
                result.append(points[max_idx])
                rdp_recursive(points, epsilon, max_idx, end_idx, result)
        
        # Run RDP
        result = [points[0]]
        rdp_recursive(points, epsilon, 0, len(points) - 1, result)
        result.append(points[-1])
        
        return result

    def adaptive_smoothing(
        self,
        points: List[Tuple[float, float]],
        aggressive: bool = True,
    ) -> List[Tuple[float, float]]:
        """
        Apply adaptive smoothing based on path complexity.
        
        Args:
            points: Input points
            aggressive: Whether to apply aggressive smoothing
            
        Returns:
            Smoothed points
        """
        if len(points) < 3:
            return points
        
        # Calculate path complexity (total variation)
        points_array = np.array(points)
        diffs = np.diff(points_array, axis=0)
        variations = np.linalg.norm(diffs, axis=1)
        total_variation = np.sum(variations)
        avg_segment = total_variation / len(variations) if len(variations) > 0 else 0
        
        # Choose method based on complexity
        if avg_segment < 2.0:
            # Simple path - use RDP for aggressive simplification
            epsilon = 2.0 if aggressive else 1.0
            return self.rdp_simplification(points, epsilon)
        elif avg_segment < 10.0:
            # Medium complexity - use Catmull-Rom
            return self.catmull_rom_spline(points, tension=0.5)
        else:
            # Complex path - use Bezier smoothing
            return self.bezier_smoothing(points)

    def smooth_svg_path(
        self,
        path_data: str,
        method: Literal["catmull-rom", "bezier", "rdp", "adaptive"] = "adaptive",
        **kwargs
    ) -> str:
        """
        Smooth an SVG path data string.
        
        Args:
            path_data: SVG path 'd' attribute
            method: Smoothing method
            **kwargs: Additional parameters
            
        Returns:
            Smoothed path data
        """
        # Parse path data (simplified version)
        # In production, use a proper SVG path parser like svg.path
        
        # For now, just detect if it's a simple line path
        commands = re.findall(r'[MmLlHhVvCcSsQqTtAaZz][^MmLlHhVvCcSsQqTtAaZz]*', path_data)
        
        if not commands:
            return path_data
        
        # Extract points from commands
        points = []
        for cmd in commands:
            letter = cmd[0].upper()
            if letter in ['M', 'L']:
                # Extract coordinates
                coords = re.findall(r'-?\d+\.?\d*', cmd[1:])
                if len(coords) >= 2:
                    points.append((float(coords[0]), float(coords[1])))
        
        if len(points) < 2:
            return path_data
        
        # Smooth points
        smoothed = self.smooth_points(points, method, **kwargs)
        
        # Reconstruct path
        if smoothed:
            new_path = f"M {smoothed[0][0]:.2f} {smoothed[0][1]:.2f}"
            for point in smoothed[1:]:
                new_path += f" L {point[0]:.2f} {point[1]:.2f}"
            return new_path
        
        return path_data

    def calculate_path_complexity(self, points: List[Tuple[float, float]]) -> dict:
        """Calculate complexity metrics for a path."""
        if len(points) < 2:
            return {"complexity": 0, "point_count": len(points)}
        
        points_array = np.array(points)
        
        # Total length
        diffs = np.diff(points_array, axis=0)
        segment_lengths = np.linalg.norm(diffs, axis=1)
        total_length = np.sum(segment_lengths)
        
        # Number of direction changes
        if len(diffs) > 1:
            angles = np.arctan2(diffs[1:, 1], diffs[1:, 0]) - np.arctan2(diffs[:-1, 1], diffs[:-1, 0])
            direction_changes = np.sum(np.abs(angles) > np.pi / 4)
        else:
            direction_changes = 0
        
        # Bounding box
        bbox_width = np.max(points_array[:, 0]) - np.min(points_array[:, 0])
        bbox_height = np.max(points_array[:, 1]) - np.min(points_array[:, 1])
        
        return {
            "complexity": float(total_length / len(points)),
            "point_count": len(points),
            "total_length": float(total_length),
            "direction_changes": int(direction_changes),
            "bbox_width": float(bbox_width),
            "bbox_height": float(bbox_height),
        }

    def compare_methods(self, points: List[Tuple[float, float]]) -> dict:
        """Compare different smoothing methods on the same points."""
        results = {}
        original_complexity = self.calculate_path_complexity(points)
        
        for method in ["catmull-rom", "bezier", "rdp", "adaptive"]:
            try:
                smoothed = self.smooth_points(points, method)
                smoothed_complexity = self.calculate_path_complexity(smoothed)
                
                results[method] = {
                    "point_count": len(smoothed),
                    "original_count": len(points),
                    "reduction": (1 - len(smoothed) / len(points)) * 100 if points else 0,
                    "complexity": smoothed_complexity,
                    "points": smoothed[:10] if len(smoothed) <= 10 else None,  # Only include for small paths
                }
            except Exception as e:
                results[method] = {"error": str(e)}
        
        results["original"] = {
            "point_count": len(points),
            "complexity": original_complexity,
        }
        
        return results
