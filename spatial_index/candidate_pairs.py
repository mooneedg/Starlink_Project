import pandas as pd
import numpy as np
import os
from skyfield.api import wgs84, load, Distance, Angle
from spatial_index.kd_tree import SpatialIndex

# To run program: python -m spatial_index.candidate_pairs


# Configuration
INPUT_FILE = "data/processed/orbit_data.parquet"
OUTPUT_FILE = "data/processed/candidate_pairs.parquet"
SEARCH_RADIUS_KM = 2.0  # Configurable threshold

def ensure_cartesian(df):
    """
    Checks if dataframe has x_km, y_km, z_km.
    If only lat/lon/alt exist, converts them to ECEF Cartesian coordinates
    using Skyfield's built-in WGS84 model.
    """
    required = ['x_km', 'y_km', 'z_km']
    if all(col in df.columns for col in required):
        return df

    print("DETECTED GEODETIC DATA: Converting Lat/Lon/Alt to Cartesian (ECEF)...")
    
    # Check for Geodetic columns
    if not all(col in df.columns for col in ['latitude', 'longitude', 'altitude_km']):
        raise ValueError("Input data missing required coordinate columns.")

    # 1. Use Skyfield's vectorized conversion
    # wgs84.latlon expects elevation in METERS, so we multiply altitude_km * 1000
    position = wgs84.latlon(
        df['latitude'].values, 
        df['longitude'].values, 
        elevation_m=df['altitude_km'].values * 1000
    )
    
    # 2. Extract the Earth-Fixed (ITRS) coordinates in km
    # This returns a (3, N) array, so we unpack it
    x, y, z = position.itrs_xyz.km

    # 3. Assign back to DataFrame
    df['x_km'] = x
    df['y_km'] = y
    df['z_km'] = z
    
    
    
    # 4. CRITICAL FIX: Drop rows with NaN or Inf in coordinates
    initial_count = len(df)
    
    # Check x, y, z for validity
    valid_mask = np.isfinite(df['x_km']) & np.isfinite(df['y_km']) & np.isfinite(df['z_km'])
    df = df[valid_mask].copy()
    
    dropped_count = initial_count - len(df)
    if dropped_count > 0:
        print(f"WARNING: Dropped {dropped_count} rows containing NaN/Inf coordinates.")
        
    print("Conversion complete.")
    return df


def process_conjunctions():
    print(f"Loading data from {INPUT_FILE}...")
    try:
        df = pd.read_parquet(INPUT_FILE)
    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found. Run Phase 2 first.")
        return

    # 1. Data Adapter: Ensure we have Cartesian coordinates for the KD-Tree
    df = ensure_cartesian(df)

    # 2. Group by Timestamp
    # This prevents O(N^2) checks across different times
    timestamps = df['timestamp'].unique()
    print(f"Processing {len(timestamps)} timestamps...")

    all_candidates = []

    for ts in timestamps:
        # Extract subset for this specific second
        group = df[df['timestamp'] == ts].reset_index(drop=True)
        
        # We need at least 2 objects to form a pair
        if len(group) < 2:
            continue

        # Extract position matrix (N, 3)
        coords = group[['x_km', 'y_km', 'z_km']].values

        # DOUBLE CHECK: Ensure no NaNs slipped through
        if not np.all(np.isfinite(coords)):
            print(f"Skipping timestamp {ts}: Data contains NaNs.")
            continue

      
        # 3. Build Spatial Index (KD-Tree)
        idx = SpatialIndex(coords)
        
        # 4. Query for pairs < Radius
        # Returns set of (i, j) indices relative to the 'group' dataframe
        pairs = idx.query_pairs(SEARCH_RADIUS_KM)
        
        if not pairs:
            continue
            
        # 5. Map indices back to NORAD IDs and calculate exact distance
        for i, j in pairs:
            obj1 = group.iloc[i]
            obj2 = group.iloc[j]
            
            # Calculate instantaneous Euclidean distance
            # KDTree gives us candidates, but let's be explicit for the output
            p1 = coords[i]
            p2 = coords[j]
            dist_km = np.linalg.norm(p1 - p2)

            all_candidates.append({
                'timestamp': ts,
                'object_1': obj1['norad_id'],
                'object_2': obj2['norad_id'],
                'instantaneous_distance_km': dist_km
            })

    # 6. Save Results
    if not all_candidates:
        print("No conjunctions found within threshold.")
        # Create empty DF with correct schema
        result_df = pd.DataFrame(columns=['timestamp', 'object_1', 'object_2', 'instantaneous_distance_km'])
    else:
        result_df = pd.DataFrame(all_candidates)
        print(f"Found {len(result_df)} candidate pairs.")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    result_df.to_parquet(OUTPUT_FILE, index=False)
    print(f"Results saved to {OUTPUT_FILE}")

def count_candidate_pairs(timestamp):
    """
    Validation function to check results for a specific timestamp.
    """
    if not os.path.exists(OUTPUT_FILE):
        print("Output file not found.")
        return 0

    df = pd.read_parquet(OUTPUT_FILE)
    
    # Filter for timestamp if provided (handling string/datetime mismatch)
    # Assuming parquet saves as datetime objects
    matches = df[df['timestamp'] == timestamp]
    
    count = len(matches)
    print(f"Validation: Timestamp {timestamp} has {count} pairs.")
    return count

if __name__ == "__main__":
    process_conjunctions()

