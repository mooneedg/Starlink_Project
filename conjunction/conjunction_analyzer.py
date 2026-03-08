import pandas as pd
import numpy as np
import os
import uuid
from skyfield.api import wgs84
from conjunction.closest_approach import compute_tca_vectorized
from conjunction.risk_score import calculate_risk_score

# To run: python -m conjunction.conjunction_analyzer

# Paths
ORBIT_FILE = "data/processed/orbit_data.parquet"
CANDIDATE_FILE = "data/processed/candidate_pairs.parquet"
OUTPUT_FILE = "data/processed/conjunction_events.parquet"

def prepare_state_vectors(df):
    """
    Converts Lat/Lon/Alt to Cartesian (x,y,z) AND estimates Velocity (vx,vy,vz).
    """
    print("Converting Geodetic to Cartesian and estimating Velocity...")
    
    # 1. Sort to ensure time-based finite differencing works
    df = df.sort_values(by=['norad_id', 'timestamp'])
    
    # 2. Position Conversion (Skyfield WGS84)
    # Convert altitude km to meters for the function
    pos = wgs84.latlon(
        df['latitude'].values, 
        df['longitude'].values, 
        elevation_m=df['altitude_km'].values * 1000
    )
    
    x, y, z = pos.itrs_xyz.km
    df['x_km'] = x
    df['y_km'] = y
    df['z_km'] = z
    
    # 3. Velocity Estimation (Finite Difference)
    # Group by satellite to prevent differencing across different objects
    # This is a vectorized approximation: v = (pos_next - pos_prev) / (2 * dt)
    # For simplicity and speed in this phase, we use simple diff: v = (pos_current - pos_prev) / dt
    
    # Calculate time delta in seconds
    df['dt'] = df.groupby('norad_id')['timestamp'].diff().dt.total_seconds()
    
    # Calculate position deltas
    df['dx'] = df.groupby('norad_id')['x_km'].diff()
    df['dy'] = df.groupby('norad_id')['y_km'].diff()
    df['dz'] = df.groupby('norad_id')['z_km'].diff()
    
    # Velocity = delta_pos / delta_time
    # Fill NA (first row of each group) with 0 or forward fill
    df['vx_kms'] = (df['dx'] / df['dt']).fillna(0)
    df['vy_kms'] = (df['dy'] / df['dt']).fillna(0)
    df['vz_kms'] = (df['dz'] / df['dt']).fillna(0)
    
    # Cleanup helper columns
    df.drop(columns=['dt', 'dx', 'dy', 'dz'], inplace=True)
    
    print("State vector preparation complete.")
    return df

def run_analysis():
    # 1. Load Data
    if not os.path.exists(CANDIDATE_FILE):
        print(f"Error: {CANDIDATE_FILE} not found. Run Phase 3 first.")
        return

    print("Loading datasets...")
    candidates = pd.read_parquet(CANDIDATE_FILE)
    orbit_data = pd.read_parquet(ORBIT_FILE)
    
    if len(candidates) == 0:
        print("No candidates to analyze.")
        return

    # 2. Prepare Physics Data (Add X,Y,Z and VX,VY,VZ)
    states = prepare_state_vectors(orbit_data)
    
    # We only need the columns relevant for physics
    states = states[['norad_id', 'timestamp', 'x_km', 'y_km', 'z_km', 'vx_kms', 'vy_kms', 'vz_kms']]

    print(f"Analyzing {len(candidates)} candidate pairs...")

    # 3. Join Datasets
    # We need to merge the 'states' table onto the 'candidates' table TWICE
    # Once for object_1, once for object_2
    
    # Join for Object 1
    merged = pd.merge(
        candidates, 
        states, 
        left_on=['object_1', 'timestamp'], 
        right_on=['norad_id', 'timestamp'],
        suffixes=('', '_1')
    )
    # Rename columns for clarity (x_km -> x1, etc)
    merged = merged.rename(columns={
        'x_km': 'x1', 'y_km': 'y1', 'z_km': 'z1',
        'vx_kms': 'vx1', 'vy_kms': 'vy1', 'vz_kms': 'vz1'
    })
    
    # Join for Object 2
    merged = pd.merge(
        merged, 
        states, 
        left_on=['object_2', 'timestamp'], 
        right_on=['norad_id', 'timestamp'],
        suffixes=('', '_2')
    )
    # Rename columns
    merged = merged.rename(columns={
        'x_km': 'x2', 'y_km': 'y2', 'z_km': 'z2',
        'vx_kms': 'vx2', 'vy_kms': 'vy2', 'vz_kms': 'vz2'
    })

    # 4. Vectorized Physics Calculation
    # Extract numpy arrays for speed
    r1 = merged[['x1', 'y1', 'z1']].values
    r2 = merged[['x2', 'y2', 'z2']].values
    v1 = merged[['vx1', 'vy1', 'vz1']].values
    v2 = merged[['vx2', 'vy2', 'vz2']].values
    
    r_rel = r2 - r1
    v_rel = v2 - v1
    
    # Compute TCA and Miss Distance
    tca_vals, miss_dists = compute_tca_vectorized(r_rel, v_rel)
    
    merged['tca_seconds'] = tca_vals
    merged['miss_distance_km'] = miss_dists
    merged['relative_velocity_kms'] = np.linalg.norm(v_rel, axis=1)

    # 5. Apply Filters (Phase Rules)
    # Rule: 0 <= tca <= 3600
    valid_events = merged[
        (merged['tca_seconds'] >= 0) & 
        (merged['tca_seconds'] <= 3600)
    ].copy()
    
    if len(valid_events) == 0:
        print("No events met the TCA valid window criteria.")
        return

    # 6. Calculate Risk Score
    valid_events['risk_score'] = calculate_risk_score(valid_events['miss_distance_km'])
    
    # 7. Final Formatting
    # Calculate exact UTC timestamp for TCA
    # timestamp is already datetime64[ns], we can add seconds directly
    valid_events['tca_timestamp'] = valid_events['timestamp'] + pd.to_timedelta(valid_events['tca_seconds'], unit='s')
    
    # Generate unique Event IDs
    valid_events['event_id'] = [str(uuid.uuid4()) for _ in range(len(valid_events))]
    
    output_columns = [
        'event_id',
        'object_1',
        'object_2',
        'tca_timestamp',
        'miss_distance_km',
        'relative_velocity_kms',
        'risk_score',
        'timestamp' # The reference timestamp
    ]
    
    final_df = valid_events[output_columns].rename(columns={'timestamp': 'reference_timestamp'})
    
    # 8. Save
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    final_df.to_parquet(OUTPUT_FILE, index=False)
    
    print(f"SUCCESS: Generated {len(final_df)} confirmed conjunction events.")
    print(f"Saved to {OUTPUT_FILE}")

def get_top_risks(n=5):
    """Validation function to inspect results"""
    if not os.path.exists(OUTPUT_FILE):
        return
    
    df = pd.read_parquet(OUTPUT_FILE)
    top = df.sort_values(by='risk_score', ascending=False).head(n)
    print(f"\n--- TOP {n} HIGH RISK EVENTS ---")
    print(top[['object_1', 'object_2', 'miss_distance_km', 'risk_score', 'tca_timestamp']].to_string(index=False))

if __name__ == "__main__":
    run_analysis()
    get_top_risks()

