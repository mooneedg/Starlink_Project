import numpy as np

def validate_coordinates(positions):
    """
    Checks if propagated coordinates are physically realistic.
    
    Args:
        positions (numpy.ndarray): Shape (3, N) array of [x, y, z] coordinates in km.
        
    Returns:
        bool: True if valid, False if invalid (e.g., inside Earth or too far).
        dict: Stats about the validation (min_altitude, max_altitude).
    """
    # 1. Calculate magnitude (radius from Earth center) for all time steps
    # positions is (3, N), so we square, sum along axis 0, and sqrt
    r_vectors = np.linalg.norm(positions, axis=0)
    
    min_r = np.min(r_vectors)
    max_r = np.max(r_vectors)
    
    # 2. Define Thresholds
    EARTH_RADIUS_KM = 6371.0
    MIN_VALID_R = EARTH_RADIUS_KM + 100  # Must be at least 100km above surface
    MAX_VALID_R = 100000.0               # Arbitrary cut-off (100,000 km) for LEO/MEO focus
    
    # 3. Check Logic
    is_valid = True
    reason = "Valid"
    
    if min_r < MIN_VALID_R:
        is_valid = False
        reason = f"CRASH WARNING: Object dips to {min_r:.2f} km (Inside Earth/Atmosphere)"
    
    if max_r > MAX_VALID_R:
        is_valid = False
        reason = f"LOST IN SPACE: Object exceeds {MAX_VALID_R} km"

    return is_valid, {
        "min_radius": min_r,
        "max_radius": max_r,
        "reason": reason
    }

