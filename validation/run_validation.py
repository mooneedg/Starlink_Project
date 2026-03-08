import pandas as pd
import os
import json
from validation.ingest_socrates import load_socrates_data
from validation.matcher import match_events
from validation.metrics import compute_metrics


# Paths
INTERNAL_FILE = "data/processed/conjunction_events.parquet"
SOCRATES_FILE = "data/external/sort-minRange.csv" # Get from here: https://celestrak.org/SOCRATES/socrates-format.php
RESULTS_FILE = "data/processed/validation_results.parquet"
METRICS_FILE = "data/processed/validation_metrics.json"


def run_validation():
   print("\n--- STARTING PHASE 5: VALIDATION ---")
  
   # 1. Load Data
   if not os.path.exists(INTERNAL_FILE):
       print("Internal events file missing. Run Phase 4 first.")
       return
   internal_df = pd.read_parquet(INTERNAL_FILE)
  
   # Ensure tca_timestamp is datetime with UTC timezone for comparison
   if internal_df['tca_timestamp'].dt.tz is None:
       internal_df['tca_timestamp'] = internal_df['tca_timestamp'].dt.tz_localize('UTC')
      
   print(f"Loaded {len(internal_df)} Internal events.")


   if not os.path.exists(SOCRATES_FILE):
       print(f"CRITICAL: SOCRATES file missing at {SOCRATES_FILE}.")
       return
      
   socrates_df = load_socrates_data(SOCRATES_FILE)


   # 1.5. TIME WINDOW SYNCHRONIZATION
   # We must restrict the 7-day SOCRATES report to our 48-hour simulation window
   # Otherwise, Recall will be artificially low
   max_internal_time = internal_df['tca_timestamp'].max()
   min_internal_time = internal_df['tca_timestamp'].min()
  
   print(f"\nSynchronizing time windows...")
   print(f"Internal Engine Span: {min_internal_time} to {max_internal_time}")
  
   initial_soc_count = len(socrates_df)
   socrates_df = socrates_df[
       (socrates_df['tca_time'] >= min_internal_time) &
       (socrates_df['tca_time'] <= max_internal_time)
   ].copy()
  
   time_span = max_internal_time - min_internal_time
   time_span_hours = time_span.total_seconds() / 3600
 
   print(
        f"Filtered SOCRATES events from {initial_soc_count} to {len(socrates_df)} "
        f"within the internal time span ({time_span_hours:.1f} hours).\n"
   )

   # 2. Run Matching
   if socrates_df.empty:
       print("Skipping matching (No external data in this time window).")
       matches = pd.DataFrame()
   else:
       matches = match_events(internal_df, socrates_df)


   # 3. Compute Metrics
   metrics = compute_metrics(
       matches,
       total_internal=len(internal_df),
       total_socrates=len(socrates_df)
   )


   # 4. Save Outputs
   os.makedirs(os.path.dirname(METRICS_FILE), exist_ok=True)
   with open(METRICS_FILE, 'w') as f:
       json.dump(metrics, f, indent=4)
   print(f"Metrics saved to {METRICS_FILE}")


   if not matches.empty:
       output_df = matches[[
           'socrates_id',
           'event_id',
           'time_error_seconds',
           'miss_distance_error_km'
       ]].rename(columns={'event_id': 'matched_internal_event_id'})
       output_df['match_status'] = 'matched'
       output_df.to_parquet(RESULTS_FILE, index=False)
       print(f"Match results saved to {RESULTS_FILE}")
   else:
       print("No matches found to save.")


   print_validation_summary(metrics)


def print_validation_summary(metrics):
   print("\n" + "="*40)
   print("      VALIDATION SUMMARY REPORT      ")
   print("="*40)
   print(f"Socrates Events (Truth Window): {metrics['total_socrates_events']}")
   print(f"Internal Events (Predictions):  {metrics['total_internal_events']}")
   print("-" * 40)
   print(f"True Positives (Hits):   {metrics['true_positives']}")
   print(f"False Negatives (Miss):  {metrics['false_negatives']}")
   print(f"False Positives (Noise): {metrics['false_positives']}")
   print("-" * 40)
   print(f"RECALL:    {metrics['recall']:.2%}")
   print(f"PRECISION: {metrics['precision']:.2%}")
   print("-" * 40)
   print(f"Avg Time Error: {metrics['mean_tca_time_error_seconds']:.2f} sec")
   print(f"Avg Dist Error: {metrics['mean_miss_distance_error_km']:.4f} km")
   print("="*40 + "\n")


if __name__ == "__main__":
   run_validation()

