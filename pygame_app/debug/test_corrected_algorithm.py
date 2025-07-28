"""
Test the CORRECTED minimum area triangle trilateration algorithm
KEY: Car CONTAINS the triangle, not the other way around
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

def test_corrected_algorithm():
    """Test the corrected algorithm where car contains triangle"""
    print("Testing CORRECTED Minimum Area Triangle Algorithm:")
    print("KEY INSIGHT: Car CONTAINS the triangle")
    print("=" * 60)
    
    # Test scenario
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
    
    # Generate candidate car center positions to test
    sensor_center_x = sum(s.x for s in sensors) / 3
    sensor_center_y = sum(s.y for s in sensors) / 3
    
    # Create a search grid around the sensor center
    grid_size = 60  # cm - search radius (expanded)
    grid_step = 4   # cm - step size (finer)
    car_center_candidates = []
    
    for dx in range(-grid_size, grid_size + 1, grid_step):
        for dy in range(-grid_size, grid_size + 1, grid_step):
            candidate = Point2D(sensor_center_x + dx, sensor_center_y + dy)
            car_center_candidates.append(candidate)
    
    print(f"\nTesting {len(car_center_candidates)} potential car center positions...")
    
    min_area = float('inf')
    best_triangle = None
    best_car_position = None
    valid_solutions = 0
    
    # For each potential car center, find the triangle formed by closest points on distance circles
    for car_center in car_center_candidates:
        # For each distance circle, find the point on the circle closest to car center
        triangle_vertices = []
        
        for sensor_pos, radius in zip(sensors, distances):
            # Vector from sensor to car center
            dx = car_center.x - sensor_pos.x
            dy = car_center.y - sensor_pos.y
            dist_to_center = math.sqrt(dx*dx + dy*dy)
            
            if dist_to_center > 0:
                # Point on circle closest to car center
                factor = radius / dist_to_center
                closest_x = sensor_pos.x + dx * factor
                closest_y = sensor_pos.y + dy * factor
                triangle_vertices.append(Point2D(closest_x, closest_y))
            else:
                # Car center is exactly on sensor (edge case)
                triangle_vertices.append(Point2D(sensor_pos.x + radius, sensor_pos.y))
        
        # Verify this is a valid configuration
        if len(triangle_vertices) == 3:
            # Verify distance constraints are satisfied
            distances_satisfied = True
            for sensor_pos, measured_distance in zip(sensors, distances):
                actual_distance = car_center.distance_to(sensor_pos)
                required_min_distance = measured_distance + CAR_RADIUS
                
                # Car center must be far enough from sensor
                if actual_distance < required_min_distance - 5.0:  # 5cm tolerance
                    distances_satisfied = False
                    break
            
            if distances_satisfied:
                # Calculate triangle area
                area = triangle_area(triangle_vertices[0], triangle_vertices[1], triangle_vertices[2])
                
                if area > 0.1 and area < min_area:  # Valid triangle
                    min_area = area
                    best_triangle = triangle_vertices
                    best_car_position = car_center
                    valid_solutions += 1
    
    print(f"\n✅ Results:")
    print(f"Found {valid_solutions} valid car positions")
    
    if best_triangle and best_car_position:
        print(f"🎯 Best triangle area: {min_area:.2f} cm²")
        print(f"🚗 Optimal car center: ({best_car_position.x:.1f}, {best_car_position.y:.1f})")
        print(f"📍 Triangle vertices (closest points on distance circles):")
        for i, vertex in enumerate(best_triangle, 1):
            print(f"   P{i}: ({vertex.x:.1f}, {vertex.y:.1f})")
        
        # Verify final solution
        print(f"\n🔍 Verification:")
        
        for i, (sensor, distance) in enumerate(zip(sensors, distances), 1):
            actual_distance = best_car_position.distance_to(sensor)
            required_distance = distance + CAR_RADIUS
            status = "✅" if actual_distance >= required_distance - 5 else "❌"
            print(f"   Sensor {i}: actual={actual_distance:.1f}, required≥{required_distance:.1f}, {status}")
        
        # Show triangle vertex distances from car center
        print(f"\n📐 Triangle vertices (detection points):")
        for i, vertex in enumerate(best_triangle, 1):
            dist = vertex.distance_to(best_car_position)
            print(f"   P{i}: ({vertex.x:.1f}, {vertex.y:.1f}), {dist:.1f}cm from car center")
            
    else:
        print("❌ No valid car position found with minimum area triangle")

if __name__ == "__main__":
    test_corrected_algorithm()