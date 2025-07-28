"""
Rethinking the constraint: What does "car contains triangle" mean?

Analysis:
1. Sensors measure distance to NEAREST car edge
2. The triangle vertices are the points on distance circles closest to car center
3. These points represent where the sensors "see" the car edges
4. The car "contains" the triangle in the sense that the car's boundaries encompass these detection points

But the detection points are ON the distance circles, not necessarily within the car's physical radius.

Maybe the constraint should be different...
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

def analyze_constraint():
    """Analyze what the constraint should actually be"""
    print("RETHINKING: What does 'car contains triangle' mean?")
    print("=" * 60)
    
    # Test scenario
    sensors = [
        Point2D(80, 110),   # Left sensor
        Point2D(200, 110),  # Right sensor  
        Point2D(140, 200)   # Top sensor (closer)
    ]
    
    distances = [50.0, 40.0, 45.0]
    
    # Car dimensions
    CAR_LENGTH = 30.0  # cm
    CAR_WIDTH = 16.0   # cm  
    CAR_RADIUS = math.sqrt((CAR_LENGTH/2)**2 + (CAR_WIDTH/2)**2)
    
    print(f"Car dimensions: {CAR_LENGTH}cm x {CAR_WIDTH}cm")
    print(f"Car diagonal radius: {CAR_RADIUS:.1f}cm")
    
    # Let's think about this differently
    # If we place the car at some position, the sensors will detect the CLOSEST car edges
    # The triangle formed by these detection points should indeed be small and fit within reasonable bounds
    
    # But maybe the constraint isn't that the triangle fits within the car's radius
    # Maybe it's that the car position should minimize the triangle area while satisfying distance constraints
    
    print(f"\nNEW APPROACH:")
    print(f"1. Find car positions that satisfy distance constraints")  
    print(f"2. Among valid positions, choose the one with minimum triangle area")
    print(f"3. Don't require triangle to fit within car radius")
    
    # Test different car positions
    test_positions = [
        Point2D(140, 150),  # Center-ish
        Point2D(130, 145),  # Slightly left
        Point2D(150, 145),  # Slightly right
    ]
    
    for pos in test_positions:
        print(f"\nTesting car position: ({pos.x:.1f}, {pos.y:.1f})")
        
        # Find closest points on distance circles
        triangle_vertices = []
        for sensor_pos, radius in zip(sensors, distances):
            dx = pos.x - sensor_pos.x
            dy = pos.y - sensor_pos.y
            dist_to_center = math.sqrt(dx*dx + dy*dy)
            
            if dist_to_center > 0:
                factor = radius / dist_to_center
                closest_x = sensor_pos.x + dx * factor
                closest_y = sensor_pos.y + dy * factor
                triangle_vertices.append(Point2D(closest_x, closest_y))
        
        # Check distance constraints
        valid = True
        for i, (sensor_pos, measured_distance) in enumerate(zip(sensors, distances), 1):
            actual_distance = pos.distance_to(sensor_pos)
            required_min_distance = measured_distance + CAR_RADIUS
            
            if actual_distance < required_min_distance - 3.0:
                valid = False
                print(f"  ❌ Violates constraint for sensor {i}")
                break
        
        if valid and len(triangle_vertices) == 3:
            area = triangle_area(triangle_vertices[0], triangle_vertices[1], triangle_vertices[2])
            print(f"  ✅ Valid position, triangle area: {area:.2f} cm²")
            
            # Show triangle vertices
            for i, vertex in enumerate(triangle_vertices, 1):
                dist_from_car = vertex.distance_to(pos)
                print(f"    P{i}: ({vertex.x:.1f}, {vertex.y:.1f}), {dist_from_car:.1f}cm from car")

if __name__ == "__main__":
    analyze_constraint()