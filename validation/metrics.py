import json
import numpy as np

def compute_metrics(matches_df, total_internal, total_socrates):
    """
    Computes precision, recall, and error statistics.
    
    Args:
        matches_df (pd.DataFrame): The validated matches.
        total_internal (int): Count of Phase 4 events.
        total_socrates (int): Count of input SOCRATES events.
        
    Returns:
        dict: Dictionary of metrics.
    """
    print("Computing metrics...")
    
    true_positives = len(matches_df)
    
    # False Negatives: Events in SOCRATES that we failed to match
    false_negatives = total_socrates - true_positives
    
    # False Positives: Events we reported that had no match in SOCRATES
    # Note: This is an estimation. Some "False Positives" might be real events SOCRATES missed,
    # but in validation, we treat SOCRATES as absolute truth.
    false_positives = total_internal - true_positives

    # Recall (Sensitivity): How many truth events did we find?
    recall = 0.0
    if total_socrates > 0:
        recall = true_positives / total_socrates

    # Precision: How many of our reports were real?
    precision = 0.0
    if total_internal > 0:
        precision = true_positives / total_internal

    # Error Statistics
    if true_positives > 0:
        mean_time_error = matches_df['time_error_seconds'].mean()
        mean_dist_error = matches_df['miss_distance_error_km'].mean()
    else:
        mean_time_error = 0.0
        mean_dist_error = 0.0

    metrics = {
        "total_socrates_events": int(total_socrates),
        "total_internal_events": int(total_internal),
        "true_positives": int(true_positives),
        "false_negatives": int(false_negatives),
        "false_positives": int(false_positives),
        "recall": float(round(recall, 4)),
        "precision": float(round(precision, 4)),
        "mean_tca_time_error_seconds": float(round(mean_time_error, 4)),
        "mean_miss_distance_error_km": float(round(mean_dist_error, 4))
    }
    
    return metrics


    