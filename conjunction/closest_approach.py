import numpy as np

def compute_tca_vectorized(r_rel, v_rel):
    """
    Computes Time of Closest Approach (TCA) and Miss Distance for arrays of vectors.
    
    Args:
        r_rel (np.array): Shape (N, 3) relative position vectors [km]
        v_rel (np.array): Shape (N, 3) relative velocity vectors [km/s]
        
    Returns:
        tuple: (tca_seconds, miss_distance_km)
    """
    # 1. Calculate dot product (r_rel . v_rel)
    # sum(axis=1) is equivalent to dot product for each row
    dot_prod = np.sum(r_rel * v_rel, axis=1)
    
    # 2. Calculate velocity magnitude squared (|v_rel|^2)
    v_mag_sq = np.sum(v_rel**2, axis=1)
    
    # Safety: Avoid division by zero for objects moving exactly parallel
    # Replace 0 with a tiny epsilon
    v_mag_sq[v_mag_sq == 0] = 1e-9
    
    # 3. Compute TCA Formula
    tca = -dot_prod / v_mag_sq
    
    # 4. Compute Position at TCA (Linear Projection)
    # r_tca = r_rel + v_rel * tca
    # We need to reshape tca to (N, 1) to broadcast multiplication against (N, 3)
    r_tca = r_rel + v_rel * tca[:, np.newaxis]
    
    # 5. Compute Scalar Miss Distance
    miss_distance = np.linalg.norm(r_tca, axis=1)
    
    return tca, miss_distance


