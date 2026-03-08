import pandas as pd
import numpy as np

def match_events(internal_df, socrates_df, time_tol_sec=300, dist_tol_km=0.5):
    """
    Matches internal events to SOCRATES events using fuzzy logic on Time and Distance.
    
    Args:
        internal_df (pd.DataFrame): Phase 4 output.
        socrates_df (pd.DataFrame): Normalized SOCRATES output.
        time_tol_sec (float): Max allowed time difference in seconds.
        dist_tol_km (float): Max allowed miss distance difference in km.
        
    Returns:
        pd.DataFrame: Merged dataframe of MATCHED events only.
    """
    if internal_df.empty or socrates_df.empty:
        return pd.DataFrame()

    print("Matching events...")

    # 1. Normalize Internal Data (Ensure Object 1 is Min, Object 2 is Max)
    # Just to be safe, though Phase 3 usually handles this.
    i_obj1 = internal_df['object_1'].astype(str)
    i_obj2 = internal_df['object_2'].astype(str)
    
    internal_df['match_obj1'] = np.where(i_obj1 < i_obj2, i_obj1, i_obj2)
    internal_df['match_obj2'] = np.where(i_obj1 < i_obj2, i_obj2, i_obj1)

    # 2. Perform Inner Join on Object Pairs
    # This drastically reduces O(N^2) complexity to O(N_matches)
    merged = pd.merge(
        socrates_df,
        internal_df,
        left_on=['object_1', 'object_2'],
        right_on=['match_obj1', 'match_obj2'],
        suffixes=('_soc', '_int')
    )

    if merged.empty:
        return pd.DataFrame()

    # 3. Calculate Deltas
    # Time delta
    time_diff = (merged['tca_timestamp'] - merged['tca_time']).abs().dt.total_seconds()
    merged['time_error_seconds'] = time_diff
    
    # Distance delta
    dist_diff = (merged['miss_distance_km'] - merged['miss_dist']).abs()
    merged['miss_distance_error_km'] = dist_diff

    # 4. Apply Tolerance Filters
    valid_matches = merged[
        (merged['time_error_seconds'] <= time_tol_sec) & 
        (merged['miss_distance_error_km'] <= dist_tol_km)
    ].copy()

    # 5. Deduplication
    # If one SOCRATES event matches multiple Internal events (rare), pick the best time match
    valid_matches = valid_matches.sort_values('time_error_seconds')
    valid_matches = valid_matches.drop_duplicates(subset=['socrates_id'], keep='first')

    print(f"Found {len(valid_matches)} valid matches.")
    return valid_matches


