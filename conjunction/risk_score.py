import numpy as np

def calculate_risk_score(miss_distance_km):
    """
    Computes a deterministic risk score based on miss distance.
    Score = 1 / (Distance + Epsilon)
    
    Args:
        miss_distance_km (np.array or float): Distance at TCA
        
    Returns:
        np.array or float: Risk Score
    """
    # Epsilon prevents division by zero for collisions (dist=0)
    EPSILON = 0.001 
    
    # Inverse relationship: Closer = Higher Score
    score = 1.0 / (miss_distance_km + EPSILON)
    
    return score


