def _should_log_trilateration(self, p1: SensorNode, p2: SensorNode, p3: SensorNode, 
                            r1: float, r2: float, r3: float) -> bool:
    """
    Only log trilateration when there are significant changes (manual mode).
    Prevents continuous logging during automatic updates.
    """
    import time
    current_time = time.time()
    
    # Create a state signature
    current_state = (
        round(p1.position.x, 1), round(p1.position.y, 1), round(r1, 1),
        round(p2.position.x, 1), round(p2.position.y, 1), round(r2, 1),
        round(p3.position.x, 1), round(p3.position.y, 1), round(r3, 1)
    )
    
    should_log = False
    
    # Log if this is the first calculation
    if self.last_trilateration_state is None:
        should_log = True
    # Log if state changed significantly
    elif current_state != self.last_trilateration_state:
        should_log = True
    # Log at most once every 2 seconds to prevent spam
    elif current_time - self.last_log_time > 2.0:
        should_log = True
    
    if should_log:
        self.last_trilateration_state = current_state
        self.last_log_time = current_time
    
    return should_log

def _perform_trilateration(self, nodes: List[SensorNode], distances: List[float]) -> Optional[Dict]:
    """
    SIMPLIFIED ROBUST MINIMUM AREA TRIANGLE ALGORITHM:
    Based on the original working approach with enhanced intersection handling.
    Only logs when manual changes occur to prevent continuous output.
    """
    if len(nodes) < 3 or len(distances) < 3:
        return None
    
    # Use the first 3 nodes
    p1, p2, p3 = nodes[:3]
    r1, r2, r3 = distances[:3]
    
    # Check if we should log this trilateration
    should_log = self._should_log_trilateration(p1, p2, p3, r1, r2, r3)
    
    if should_log:
        print(f"\n🔧 Enhanced Minimum Area Triangle Algorithm")
        print(f"📍 Distance circles:")
        print(f"   Circle 1: center=({p1.position.x:.1f}, {p1.position.y:.1f}), radius={r1:.1f}cm")
        print(f"   Circle 2: center=({p2.position.x:.1f}, {p2.position.y:.1f}), radius={r2:.1f}cm")
        print(f"   Circle 3: center=({p3.position.x:.1f}, {p3.position.y:.1f}), radius={r3:.1f}cm")
    
    # Find intersection points between each pair of circles (like original)
    int_12 = self._circle_intersections(p1.position, r1, p2.position, r2)
    int_13 = self._circle_intersections(p1.position, r1, p3.position, r3)
    int_23 = self._circle_intersections(p2.position, r2, p3.position, r3)
    
    if should_log:
        print(f"🔍 Circle intersections:")
        print(f"   Circle 1-2: {len(int_12) if int_12 else 0} points")
        print(f"   Circle 1-3: {len(int_13) if int_13 else 0} points")
        print(f"   Circle 2-3: {len(int_23) if int_23 else 0} points")
    
    # If we have enough intersections, use the original minimum area approach
    intersections = []
    if int_12:
        intersections.extend([(p, 1, 2) for p in int_12])
    if int_13:
        intersections.extend([(p, 1, 3) for p in int_13])
    if int_23:
        intersections.extend([(p, 2, 3) for p in int_23])
    
    if len(intersections) >= 3:
        # Original minimum area triangle approach
        min_area = float('inf')
        best_triangle = None
        
        for i in range(len(intersections)):
            for j in range(i + 1, len(intersections)):
                for k in range(j + 1, len(intersections)):
                    # Check if points are from different circle pairs
                    circles_i = set(intersections[i][1:])
                    circles_j = set(intersections[j][1:])
                    circles_k = set(intersections[k][1:])
                    
                    # Each point should be from different circle intersections
                    if len(circles_i | circles_j | circles_k) >= 3:
                        p_i, p_j, p_k = intersections[i][0], intersections[j][0], intersections[k][0]
                        area = self._triangle_area(p_i, p_j, p_k)
                        
                        if 0.1 < area < min_area:  # Avoid degenerate triangles
                            min_area = area
                            best_triangle = [p_i, p_j, p_k]
        
        if best_triangle:
            # Calculate centroid (original approach)
            x = sum(p.x for p in best_triangle) / 3
            y = sum(p.y for p in best_triangle) / 3
            position = Point2D(x, y)
            
            excircle = self._calculate_excircle(best_triangle)
            
            if should_log:
                print(f"✅ Found intersection-based triangle (area: {min_area:.2f})")
            
            return {
                'position': position,
                'triangle': best_triangle,
                'excircle': excircle,
                'algorithm_info': {
                    'type': 'minimum_area_triangle',
                    'area': min_area
                }
            }
    
    # Enhanced fallback for partial intersections
    if should_log:
        print(f"⚠️ Using enhanced fallback ({len(intersections)} intersections)")
    
    # Use analytical trilateration as fallback
    analytical_pos = self._analytical_trilateration_robust(p1.position, r1, p2.position, r2, p3.position, r3)
    
    if analytical_pos:
        if should_log:
            print(f"✅ Analytical fallback position: ({analytical_pos.x:.1f}, {analytical_pos.y:.1f})")
        
        return {
            'position': analytical_pos,
            'triangle': None,
            'excircle': None,
            'algorithm_info': {
                'type': 'analytical_fallback',
                'method': 'least_squares'
            }
        }
    
    # Ultimate fallback - weighted centroid
    if should_log:
        print(f"⚠️ Using weighted centroid fallback")
    
    # Weight by inverse of distance (closer sensors have more influence)
    total_weight = 0.0
    weighted_x = 0.0
    weighted_y = 0.0
    
    for sensor, radius in [(p1, r1), (p2, r2), (p3, r3)]:
        weight = 1.0 / max(radius, 1.0)  # Avoid division by zero
        weighted_x += sensor.position.x * weight
        weighted_y += sensor.position.y * weight
        total_weight += weight
    
    if total_weight > 0:
        center_x = weighted_x / total_weight
        center_y = weighted_y / total_weight
        fallback_position = Point2D(center_x, center_y)
        
        return {
            'position': fallback_position,
            'triangle': None,
            'excircle': None,
            'algorithm_info': {
                'type': 'weighted_centroid',
                'method': 'inverse_distance_weighting'
            }
        }
    
    return None
