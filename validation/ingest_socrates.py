import pandas as pd
import numpy as np
import os

def load_socrates_data(filepath):
    """
    Loads SOCRATES CSV data, maps the official CelesTrak columns, 
    and normalizes object pairs for comparison.
    """
    if not os.path.exists(filepath):
        print(f"WARNING: SOCRATES file not found at {filepath}")
        return pd.DataFrame()

    print(f"Loading SOCRATES report from {filepath}...")
    
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return pd.DataFrame()

    # The exact columns from the CelesTrak CSV format
    required = ['NORAD_CAT_ID_1', 'NORAD_CAT_ID_2', 'TCA', 'TCA_RANGE']
    if not all(col in df.columns for col in required):
        print(f"Error: CSV missing required columns. Found: {df.columns}")
        return pd.DataFrame()

    # Generate Unique IDs for SOCRATES events
    df['socrates_id'] = range(len(df))

    # Normalize Pairs (Min/Max Sort) to handle (A, B) vs (B, A) matching
    p_norad = df['NORAD_CAT_ID_1'].astype(str)
    s_norad = df['NORAD_CAT_ID_2'].astype(str)
    
    df['object_1'] = np.where(p_norad < s_norad, p_norad, s_norad)
    df['object_2'] = np.where(p_norad < s_norad, s_norad, p_norad)

    # Standardize Time and Distance
    # Convert 'TCA' to UTC datetime objects
    df['tca_time'] = pd.to_datetime(df['TCA'], utc=True)
    
    # 'TCA_RANGE' is the miss distance in km
    df['miss_dist'] = df['TCA_RANGE'].astype(float)

    # Return clean subset required for matching
    clean_df = df[['socrates_id', 'object_1', 'object_2', 'tca_time', 'miss_dist']].copy()
    
    print(f"Successfully loaded and normalized {len(clean_df)} SOCRATES events.")
    return clean_df


