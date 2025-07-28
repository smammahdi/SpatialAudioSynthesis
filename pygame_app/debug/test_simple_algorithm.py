"""
Test the simplified minimum area triangle algorithm
"""
import math
from typing import Optional, Dict, List

class Point2D:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
    
    def distance_to(self, other: 'Point2D') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

def sample_circle_points(center: Point2D, radius: float, num_samples: int = 24) -> List[Point2D]:
    """Sample points uniformly around a circle"""
    points = []
    for i in range(num_samples):
        angle = (2 * math.pi * i) / num_samples
        x = center.x + radius * math.cos(angle)
        y = center.y + radius * math.sin(angle)
        points.append(Point2D(x, y))
    return points

def triangle_area(p1: Point2D, p2: Point2D, p3: Point2D) -> float:
    """Calculate area of a triangle using cross product"""
    return 0.5 * abs((p1.x * (p2.y - p3.y) + p2.x * (p3.y - p1.y) + p3.x * (p1.y - p2.y)))

def calculate_excircle(triangle_vertices: List[Point2D]) -> Optional[Dict]:
    """Calculate the excircle (circumcircle) of a triangle."""
    if len(triangle_vertices) != 3:
        return None
    
    p1, p2, p3 = triangle_vertices
    
    # Calculate circumcenter using the formula
    ax, ay = p1.x, p1.y
    bx, by = p2.x, p2.y
    cx, cy = p3.x, p3.y
    
    D = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    
    if abs(D) < 1e-6:  # Degenerate triangle
        return None
    
    ux = ((ax*ax + ay*ay) * (by - cy) + (bx*bx + by*by) * (cy - ay) + (cx*cx + cy*cy) * (ay - by)) / D
    uy = ((ax*ax + ay*ay) * (cx - bx) + (bx*bx + by*by) * (ax - cx) + (cx*cx + cy*cy) * (bx - ax)) / D
    
    center = Point2D(ux, uy)
    radius = center.distance_to(p1)
    
    return {
        'center': center,
        'radius': radius
    }

def test_simple_algorithm():
    """Test the simple minimum area triangle algorithm"""
    print("Testing SIMPLE Minimum Area Triangle Algorithm:")
    print("=" * 60)
    
    # Test scenario similar to the screenshot
    sensors = [
        Point2D(80, 110),   # Left sensor
        Point2D(200, 110),  # Right sensor  
        Point2D(140, 240)   # Top sensor
    ]
    
    distances = [50.0, 40.0, 45.0]  # Distance measurements
    
    # Car dimensions
    CAR_LENGTH = 30.0  # cm
    CAR_WIDTH = 16.0   # cm  
    CAR_RADIUS = math.sqrt((CAR_LENGTH/2)**2 + (CAR_WIDTH/2)**2)
    
    print(f"Sensor positions:")
    for i, sensor in enumerate(sensors, 1):
        print(f"  Sensor {i}: ({sensor.x}, {sensor.y})")
    
    print(f"\nDistance measurements: {distances}")
    print(f"Car dimensions: {CAR_LENGTH}cm x {CAR_WIDTH}cm")
    
    # Sample points on each distance circle perimeter
    num_samples = 24
    circle_points = [
        sample_circle_points(sensors[0], distances[0], num_samples),
        sample_circle_points(sensors[1], distances[1], num_samples),
        sample_circle_points(sensors[2], distances[2], num_samples)
    ]
    
    min_area = float('inf')
    best_triangle = None
    
    total_combinations = num_samples ** 3
    print(f"\nTesting {total_combinations} triangle combinations...")
    
    # Try all combinations of points (one from each circle)
    for p1_point in circle_points[0]:
        for p2_point in circle_points[1]:
            for p3_point in circle_points[2]:
                # Calculate triangle area
                area = triangle_area(p1_point, p2_point, p3_point)
                
                # Skip degenerate triangles
                if area > 50.0 and area < min_area:  # At least 50 cm² to avoid degenerate triangles
                    min_area = area
                    best_triangle = [p1_point, p2_point, p3_point]
    
    if best_triangle:
        # Calculate triangle centroid as car center (SIMPLE APPROACH)
        car_center = Point2D(
            sum(p.x for p in best_triangle) / 3,
            sum(p.y for p in best_triangle) / 3
        )
        
        # Calculate excircle for visualization
        excircle = calculate_excircle(best_triangle)
        
        print(f"\n✅ Results:")
        print(f"🎯 Minimum triangle area: {min_area:.2f} cm²")
        print(f"🚗 Car center (triangle centroid): ({car_center.x:.1f}, {car_center.y:.1f})")
        print(f"📍 Triangle vertices:")
        for i, vertex in enumerate(best_triangle, 1):
            print(f"   P{i}: ({vertex.x:.1f}, {vertex.y:.1f})")
        
        if excircle:
            print(f"⭕ Excircle: center=({excircle['center'].x:.1f}, {excircle['center'].y:.1f}), radius={excircle['radius']:.1f}cm")
        
        print(f"\n🔍 Verification:")
        print(f"This is the correct rendering order:")
        print(f"1. Draw distance circles")
        print(f"2. Draw triangle (yellow)")
        print(f"3. Draw excircle (purple)")
        print(f"4. Draw car at triangle centroid with proper orientation")
        
    else:
        print("❌ No valid triangle found")

if __name__ == "__main__":
    test_simple_algorithm()