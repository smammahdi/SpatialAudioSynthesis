"""
Test the minimum area triangle trilateration algorithm
"""
import math
from typing import Optional, Dict, List

class Point2D:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
    
    def distance_to(self, other: 'Point2D') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

class MockSensorNode:
    def __init__(self, x: float, y: float):
        self.position = Point2D(x, y)

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

def verify_car_position(car_center: Point2D, sensor_positions: List[Point2D], distances: List[float], car_radius: float) -> bool:
    """Verify that a car center position satisfies distance constraints."""
    tolerance = 2.0  # 2cm tolerance
    
    for sensor_pos, measured_distance in zip(sensor_positions, distances):
        distance_to_sensor = car_center.distance_to(sensor_pos)
        required_distance = measured_distance + car_radius
        
        # Car center must be far enough from sensor
        if distance_to_sensor < required_distance - tolerance:
            return False
    
    return True

def find_optimal_car_position(triangle_vertices: List[Point2D], sensor_positions: List[Point2D], distances: List[float], car_radius: float) -> Optional[Point2D]:
    """Find the optimal car center position within a triangle that satisfies distance constraints."""
    if len(triangle_vertices) != 3 or len(sensor_positions) != 3 or len(distances) != 3:
        return None
    
    # Start with triangle centroid as initial estimate
    centroid = Point2D(
        sum(p.x for p in triangle_vertices) / 3,
        sum(p.y for p in triangle_vertices) / 3
    )
    
    # Check if centroid satisfies distance constraints
    if verify_car_position(centroid, sensor_positions, distances, car_radius):
        return centroid
    
    # If centroid doesn't work, try to find a valid position within the triangle
    best_position = None
    min_distance_to_centroid = float('inf')
    
    # Generate candidate points within the triangle using barycentric coordinates
    for alpha in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
        for beta in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
            gamma = 1.0 - alpha - beta
            if gamma > 0:  # Valid barycentric coordinates
                # Calculate point using barycentric coordinates
                candidate = Point2D(
                    alpha * triangle_vertices[0].x + beta * triangle_vertices[1].x + gamma * triangle_vertices[2].x,
                    alpha * triangle_vertices[0].y + beta * triangle_vertices[1].y + gamma * triangle_vertices[2].y
                )
                
                if verify_car_position(candidate, sensor_positions, distances, car_radius):
                    distance_to_centroid = candidate.distance_to(centroid)
                    if distance_to_centroid < min_distance_to_centroid:
                        min_distance_to_centroid = distance_to_centroid
                        best_position = candidate
    
    return best_position

def test_min_area_triangle_algorithm():
    """Test the minimum area triangle algorithm"""
    print("Testing Minimum Area Triangle Algorithm:")
    print("=" * 50)
    
    # Test scenario: similar to what user showed in screenshot
    sensors = [
        Point2D(80, 110),   # Left sensor
        Point2D(200, 110),  # Right sensor  
        Point2D(140, 240)   # Top sensor
    ]
    
    distances = [50.0, 40.0, 45.0]  # Distance measurements
    
    # Car dimensions (corrected)
    CAR_LENGTH = 30.0  # cm
    CAR_WIDTH = 16.0   # cm  
    CAR_RADIUS = math.sqrt((CAR_LENGTH/2)**2 + (CAR_WIDTH/2)**2)  # ~17cm diagonal
    
    print(f"Sensor positions:")
    for i, sensor in enumerate(sensors, 1):
        print(f"  Sensor {i}: ({sensor.x}, {sensor.y})")
    
    print(f"\nDistance measurements: {distances}")
    print(f"Car dimensions: {CAR_LENGTH}cm x {CAR_WIDTH}cm (radius ~{CAR_RADIUS:.1f}cm)")
    
    # Sample points on each distance circle perimeter
    num_samples = 16  # Optimized for performance
    circle_points = [
        sample_circle_points(sensors[0], distances[0], num_samples),
        sample_circle_points(sensors[1], distances[1], num_samples),
        sample_circle_points(sensors[2], distances[2], num_samples)
    ]
    
    min_area = float('inf')
    best_triangle = None
    best_car_position = None
    valid_triangles = 0
    
    total_combinations = num_samples ** 3
    print(f"\nTesting {total_combinations} triangle combinations...")
    
    # Try all combinations of points (one from each circle)
    for p1_point in circle_points[0]:
        for p2_point in circle_points[1]:
            for p3_point in circle_points[2]:
                triangle_vertices = [p1_point, p2_point, p3_point]
                
                # Calculate triangle area
                area = triangle_area(p1_point, p2_point, p3_point)
                
                # Skip degenerate triangles
                if area < 10.0:  # Less than 10 cm²
                    continue
                
                # Find the optimal car center position within this triangle
                car_center = find_optimal_car_position(triangle_vertices, sensors, distances, CAR_RADIUS)
                
                if car_center:
                    # Verify the car center satisfies distance constraints
                    if verify_car_position(car_center, sensors, distances, CAR_RADIUS):
                        valid_triangles += 1
                        
                        if area < min_area:
                            min_area = area
                            best_triangle = triangle_vertices
                            best_car_position = car_center
    
    print(f"\n✅ Results:")
    print(f"Found {valid_triangles} valid triangles")
    
    if best_triangle and best_car_position:
        print(f"🎯 Best triangle area: {min_area:.2f} cm²")
        print(f"🚗 Optimal car center: ({best_car_position.x:.1f}, {best_car_position.y:.1f})")
        print(f"📍 Triangle vertices:")
        for i, vertex in enumerate(best_triangle, 1):
            print(f"   P{i}: ({vertex.x:.1f}, {vertex.y:.1f})")
        
        # Verify final solution
        print(f"\n🔍 Verification:")
        for i, (sensor, distance) in enumerate(zip(sensors, distances), 1):
            actual_distance = best_car_position.distance_to(sensor)
            required_distance = distance + CAR_RADIUS
            print(f"   Sensor {i}: actual={actual_distance:.1f}, required≥{required_distance:.1f}, ✅" if actual_distance >= required_distance - 2 else f"   Sensor {i}: actual={actual_distance:.1f}, required≥{required_distance:.1f}, ❌")
    else:
        print("❌ No valid minimum area triangle found")

if __name__ == "__main__":
    test_min_area_triangle_algorithm()