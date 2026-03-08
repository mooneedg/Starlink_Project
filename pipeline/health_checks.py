import os
import time
import pandas as pd
import json
import logging

def verify_tle_freshness(db_path="database/SpaceData.db", max_age_hours=24):
    """Checks if the database has been updated recently."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"CRITICAL: Database not found at {db_path}")
    
    file_age_seconds = time.time() - os.path.getmtime(db_path)
    file_age_hours = file_age_seconds / 3600
    
    if file_age_hours > max_age_hours:
        logging.warning(f"DATA STALE: {db_path} is {file_age_hours:.2f} hours old. Ingestion may have failed.")
        return False
    return True

def verify_propagation_output(parquet_path="data/processed/orbit_data.parquet"):
    """Ensures the orbital mechanics engine actually produced data."""
    if not os.path.exists(parquet_path):
        raise FileNotFoundError(f"CRITICAL: Propagation output missing at {parquet_path}")
    
    # Check file size (must be > 1MB to be considered a valid swarm propagation)
    size_mb = os.path.getsize(parquet_path) / (1024 * 1024)
    if size_mb < 1.0:
        raise ValueError(f"CRITICAL: Propagation output is suspiciously small ({size_mb:.2f} MB).")
    return True

def verify_conjunction_output(parquet_path="data/processed/conjunction_events.parquet"):
    """Ensures the spatial filter and TCA math produced events."""
    if not os.path.exists(parquet_path):
        raise FileNotFoundError(f"CRITICAL: Conjunction output missing at {parquet_path}")
    
    df = pd.read_parquet(parquet_path)
    if df.empty:
        logging.warning("No conjunction events found. This is highly unusual for LEO.")
        return False
    return True

def verify_validation_metrics(json_path="data/processed/validation_metrics.json"):
    """Reads the validation output and warns if the model is degrading."""
    if not os.path.exists(json_path):
        logging.warning("SOCRATES validation file missing. Skipping accuracy checks.")
        return None
        
    with open(json_path, 'r') as f:
        metrics = json.load(f)
        
    recall = metrics.get('recall', 0.0)
    if recall < 0.50:
        logging.warning(f"DEGRADATION ALERT: Validation Recall dropped to {recall*100:.1f}%")
        
    return metrics