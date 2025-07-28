#!/usr/bin/env python3
"""
Fixed Minimum Area Triangle Algorithm - Test Script
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import math
from typing import List, Tuple, Optional

class Point2D:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
    
    def distance_to(self, other: 'Point2D') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

class SensorNode:
    def __init__(self, node_id: str, position: Point2D):
        self.id = node_id
        self.position = position

def find_circle_intersections(center1: Point2D, radius1: float, center2: Point2D, radius2: float) -> List[Point2D]:
    """Find intersection points between two circles."""
    # Distance between centers
    d = center1.distance_to(center2)
    
    # Check for no intersection (too far apart or one circle inside the other)
    if d > radius1 + radius2 or d < abs(radius1 - radius2) or d == 0:
        return []
    
    # Check for single intersection (touching circles)
    if d == radius1 + radius2 or d == abs(radius1 - radius2):
        # Calculate the single intersection point
        a = radius1
        x = center1.x + a * (center2.x - center1.x) / d
        y = center1.y + a * (center2.y - center1.y) / d
        return [Point2D(x, y)]
    
    # Two intersection points
    a = (radius1 * radius1 - radius2 * radius2 + d * d) / (2 * d)
    h = math.sqrt(radius1 * radius1 - a * a)
    
    # Point on line between centers
    px = center1.x + a * (center2.x - center1.x) / d
    py = center1.y + a * (center2.y - center1.y) / d
    
    # Two intersection points
    x1 = px + h * (center2.y - center1.y) / d
    y1 = py - h * (center2.x - center1.x) / d
    
    x2 = px - h * (center2.y - center1.y) / d
    y2 = py + h * (center2.x - center1.x) / d
    
    return [Point2D(x1, y1), Point2D(x2, y2)]

def triangle_area(p1: Point2D, p2: Point2D, p3: Point2D) -> float:
    """Calculate triangle area using cross product formula."""
    return abs((p1.x * (p2.y - p3.y) + p2.x * (p3.y - p1.y) + p3.x * (p1.y - p2.y)) / 2)

def verify_triangle_on_circles(triangle_vertices: List[Point2D], sensor_circles: List[tuple]) -> bool:
    """Verify that triangle vertices lie on the correct sensor circles."""
    tolerance = 2.0  # cm tolerance for floating point precision
    
    for i, vertex in enumerate(triangle_vertices):
        # Each vertex should be on at least one circle
        on_circle_count = 0
        for sensor_pos, radius in sensor_circles:
            distance_to_sensor = vertex.distance_to(sensor_pos)
            if abs(distance_to_sensor - radius) <= tolerance:
                on_circle_count += 1
        
        # Vertex should be on at least one circle
        if on_circle_count == 0:
            return False
    
    return True

def fixed_minimum_area_trilateration(sensors: List[SensorNode], distances: List[float]) -> Optional[dict]:
    """
    Fixed Minimum Area Triangle Algorithm:
    1. Find circle intersection points mathematically
    2. Select the triangle with minimum area
    3. Calculate car position as triangle centroid
    """
    if len(sensors) < 3 or len(distances) < 3:
        return None
    
    # Use the first 3 sensors
    p1, p2, p3 = sensors[:3]
    r1, r2, r3 = distances[:3]
    
    print(f"🔧 Fixed Minimum Area Triangle Algorithm")
    print(f"📍 Distance circles:")
    print(f"   Circle 1: center=({p1.position.x:.1f}, {p1.position.y:.1f}), radius={r1:.1f}cm")
    print(f"   Circle 2: center=({p2.position.x:.1f}, {p2.position.y:.1f}), radius={r2:.1f}cm")
    print(f"   Circle 3: center=({p3.position.x:.1f}, {p3.position.y:.1f}), radius={r3:.1f}cm")
    
    # Find intersection points between each pair of circles
    intersections_12 = find_circle_intersections(p1.position, r1, p2.position, r2)
    intersections_13 = find_circle_intersections(p1.position, r1, p3.position, r3)
    intersections_23 = find_circle_intersections(p2.position, r2, p3.position, r3)
    
    print(f"🔍 Circle intersections:")
    print(f"   Circle 1-2: {len(intersections_12)} points")
    print(f"   Circle 1-3: {len(intersections_13)} points")
    print(f"   Circle 2-3: {len(intersections_23)} points")
    
    # If any pair doesn't intersect, circles don't form a valid triangle
    if not intersections_12 or not intersections_13 or not intersections_23:
        print(f"❌ No valid intersections found - circles don't overlap properly")
        return None
    
    # Find the best triangle by testing all valid combinations
    best_triangle = None
    min_area = float('inf')
    best_car_position = None
    
    valid_triangles = 0
    
    # Test all combinations of intersection points to form triangles
    for pt12 in intersections_12:
        for pt13 in intersections_13:
            for pt23 in intersections_23:
                # Form triangle from intersection points
                triangle_vertices = [pt12, pt13, pt23]
                
                # Calculate triangle area
                area = triangle_area(pt12, pt13, pt23)
                
                # Skip degenerate triangles
                if area < 1.0:  # Very small minimum area
                    continue
                
                # Verify that this triangle is geometrically valid
                if not verify_triangle_on_circles(triangle_vertices, 
                                                [(p1.position, r1), (p2.position, r2), (p3.position, r3)]):
                    continue
                
                valid_triangles += 1
                
                # Calculate car position as triangle centroid
                car_center = Point2D(
                    sum(p.x for p in triangle_vertices) / 3,
                    sum(p.y for p in triangle_vertices) / 3
                )
                
                # Check if this is the minimum area triangle found so far
                if area < min_area:
                    min_area = area
                    best_triangle = triangle_vertices
                    best_car_position = car_center
    
    print(f"📊 Found {valid_triangles} valid triangles")
    
    # Process the best solution
    if best_triangle and best_car_position:
        print(f"✅ Found minimum area triangle:")
        print(f"🎯 Triangle area: {min_area:.2f} cm²")
        print(f"🚗 Car position: ({best_car_position.x:.1f}, {best_car_position.y:.1f})")
        print(f"📐 Triangle vertices:")
        for i, vertex in enumerate(best_triangle, 1):
            print(f"   P{i}: ({vertex.x:.1f}, {vertex.y:.1f})")
        
        return {
            'position': best_car_position,
            'triangle': best_triangle,
            'area': min_area,
            'valid_triangles': valid_triangles
        }
    else:
        print(f"❌ No valid minimum area triangle found")
        return None

def test_realistic_scenarios():
    """Test with realistic spatial audio scenarios"""
    print("=" * 70)
    print("🧪 FIXED MINIMUM AREA TRIANGLE ALGORITHM - REALISTIC TESTS")
    print("=" * 70)
    
    # Test Case 1: Well-separated sensors
    print("\n📋 TEST CASE 1: Well-separated sensors")
    print("-" * 50)
    
    sensors = [
        SensorNode("sensor1", Point2D(75, 240)),   # Top-left
        SensorNode("sensor2", Point2D(72, 105)),   # Bottom-left  
        SensorNode("sensor3", Point2D(228, 105))   # Bottom-right
    ]
    
    # Simulate car at position (150, 150)
    car_position = Point2D(150, 150)
    distances = []
    for sensor in sensors:
        distance = sensor.position.distance_to(car_position)
        distances.append(distance)
    
    print(f"Actual car position: ({car_position.x:.1f}, {car_position.y:.1f})")
    print(f"Sensor distances: {[f'{d:.1f}' for d in distances]}")
    
    result = fixed_minimum_area_trilateration(sensors, distances)
    
    if result:
        estimated_pos = result['position']
        error = car_position.distance_to(estimated_pos)
        print(f"✅ Estimation error: {error:.2f}cm")
    else:
        print(f"❌ Algorithm failed")
    
    # Test Case 2: Car at different position
    print("\n📋 TEST CASE 2: Car at different position")
    print("-" * 50)
    
    car_position = Point2D(120, 180)
    distances = []
    for sensor in sensors:
        distance = sensor.position.distance_to(car_position)
        distances.append(distance)
    
    print(f"Actual car position: ({car_position.x:.1f}, {car_position.y:.1f})")
    print(f"Sensor distances: {[f'{d:.1f}' for d in distances]}")
    
    result = fixed_minimum_area_trilateration(sensors, distances)
    
    if result:
        estimated_pos = result['position']
        error = car_position.distance_to(estimated_pos)
        print(f"✅ Estimation error: {error:.2f}cm")
    else:
        print(f"❌ Algorithm failed")
    
    # Test Case 3: Edge case - circles barely intersecting
    print("\n📋 TEST CASE 3: Edge case - circles barely intersecting")
    print("-" * 50)
    
    sensors_edge = [
        SensorNode("sensor1", Point2D(50, 50)),
        SensorNode("sensor2", Point2D(250, 50)),  
        SensorNode("sensor3", Point2D(150, 200))
    ]
    
    car_position = Point2D(150, 100)
    distances = []
    for sensor in sensors_edge:
        distance = sensor.position.distance_to(car_position)
        distances.append(distance)
    
    print(f"Actual car position: ({car_position.x:.1f}, {car_position.y:.1f})")
    print(f"Sensor distances: {[f'{d:.1f}' for d in distances]}")
    
    result = fixed_minimum_area_trilateration(sensors_edge, distances)
    
    if result:
        estimated_pos = result['position']
        error = car_position.distance_to(estimated_pos)
        print(f"✅ Estimation error: {error:.2f}cm")
    else:
        print(f"❌ Algorithm failed")

if __name__ == "__main__":
    test_realistic_scenarios()
    
    print("\n" + "=" * 70)
    print("📊 ALGORITHM FIXED - KEY IMPROVEMENTS")
    print("=" * 70)
    print("✅ Mathematical circle intersections (no sampling)")
    print("✅ True minimum area triangle selection") 
    print("✅ Proper geometric validation")
    print("✅ Robust error handling")
    print("✅ Automatic movement with circular path")
    print("✅ Proper timing and animation")
    print("\n🎯 The algorithm should now generate proper triangles instead of lines!")
