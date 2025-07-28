"""
Debug the corrected algorithm to understand why no valid positions are found
"""
import math
from typing import Optional, Dict, List

class Point2D:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
    
    def distance_to(self, other: 'Point2D') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

def triangle_area(p1: Point2D, p2: Point2D, p3: Point2D) -> float:
    """Calculate area of a triangle using cross product"""
    return 0.5 * abs((p1.x * (p2.y - p3.y) + p2.x * (p3.y - p1.y) + p3.x * (p1.y - p2.y)))

def triangle_fits_in_car(triangle_vertices: List[Point2D], car_center: Point2D, car_radius: float) -> bool:
    """Check if a triangle fits entirely within the car's boundaries."""
    if len(triangle_vertices) != 3:
        return False
    
    # Check that all triangle vertices are within the car's radius
    for vertex in triangle_vertices:
        distance_from_car_center = vertex.distance_to(car_center)
        if distance_from_car_center > car_radius:
            return False
    
    return True

def debug_algorithm():
    """Debug version with detailed output"""
    print("DEBUG: Corrected Algorithm Analysis")
    print("=" * 50)
    
    # Test scenario
    sensors = [
        Point2D(80, 110),   # Left sensor
        Point2D(200, 110),  # Right sensor  
        Point2D(140, 240)   # Top sensor (modified to be closer)
    ]
    
    distances = [50.0, 40.0, 45.0]
    
    # Car dimensions
    CAR_LENGTH = 30.0  # cm
    CAR_WIDTH = 16.0   # cm  
    CAR_RADIUS = math.sqrt((CAR_LENGTH/2)**2 + (CAR_WIDTH/2)**2)  # ~17cm diagonal
    
    print(f"Car radius: {CAR_RADIUS:.1f}cm")
    
    # Test a specific car center position
    sensor_center_x = sum(s.x for s in sensors) / 3
    sensor_center_y = sum(s.y for s in sensors) / 3
    test_car_center = Point2D(sensor_center_x, sensor_center_y)
    
    print(f"\nTesting car center at: ({test_car_center.x:.1f}, {test_car_center.y:.1f})")
    
    # Find closest points on each distance circle
    triangle_vertices = []
    
    for i, (sensor_pos, radius) in enumerate(zip(sensors, distances), 1):
        # Vector from sensor to car center
        dx = test_car_center.x - sensor_pos.x
        dy = test_car_center.y - sensor_pos.y
        dist_to_center = math.sqrt(dx*dx + dy*dy)
        
        print(f"\nSensor {i}: ({sensor_pos.x}, {sensor_pos.y}), radius={radius}")
        print(f"  Distance from car center to sensor: {dist_to_center:.1f}cm")
        
        if dist_to_center > 0:
            # Point on circle closest to car center
            factor = radius / dist_to_center
            closest_x = sensor_pos.x + dx * factor
            closest_y = sensor_pos.y + dy * factor
            closest_point = Point2D(closest_x, closest_y)
            triangle_vertices.append(closest_point)
            
            # Distance from car center to this closest point
            dist_to_closest = closest_point.distance_to(test_car_center)
            print(f"  Closest point on circle: ({closest_x:.1f}, {closest_y:.1f})")
            print(f"  Distance from car center to closest point: {dist_to_closest:.1f}cm")
            print(f"  Fits in car? {'✅' if dist_to_closest <= CAR_RADIUS else '❌'}")
    
    if len(triangle_vertices) == 3:
        area = triangle_area(triangle_vertices[0], triangle_vertices[1], triangle_vertices[2])
        fits_in_car = triangle_fits_in_car(triangle_vertices, test_car_center, CAR_RADIUS)
        
        print(f"\nTriangle analysis:")
        print(f"  Area: {area:.2f} cm²")
        print(f"  Fits in car: {'✅' if fits_in_car else '❌'}")
        
        # Check distance constraints
        print(f"\nDistance constraint check:")
        for i, (sensor_pos, measured_distance) in enumerate(zip(sensors, distances), 1):
            actual_distance = test_car_center.distance_to(sensor_pos)
            required_min_distance = measured_distance + CAR_RADIUS
            satisfies = actual_distance >= required_min_distance - 3.0
            
            print(f"  Sensor {i}: actual={actual_distance:.1f}, required≥{required_min_distance:.1f}, {'✅' if satisfies else '❌'}")
    
    # Let's try with a different approach - what if we relax the car radius constraint?
    print(f"\n" + "="*50)
    print("ANALYSIS: What if we use a larger effective car radius?")
    
    # Maybe the car diagonal isn't the right constraint. Let's try half-length + half-width
    effective_car_radius = max(CAR_LENGTH/2, CAR_WIDTH/2)  # 15cm
    print(f"Trying effective car radius: {effective_car_radius:.1f}cm")
    
    fits_with_larger_radius = triangle_fits_in_car(triangle_vertices, test_car_center, effective_car_radius)
    print(f"Triangle fits with larger radius: {'✅' if fits_with_larger_radius else '❌'}")
    
    # Show distances again
    for i, vertex in enumerate(triangle_vertices, 1):
        dist = vertex.distance_to(test_car_center)
        print(f"  P{i} distance from car center: {dist:.1f}cm")

if __name__ == "__main__":
    debug_algorithm()