import os
import time
import datetime
from datetime import timezone # NEW
import subprocess
import logging
from pipeline import health_checks
from reporting import report_generator

# --- Setup Logging ---
os.makedirs('logs', exist_ok=True)
# FIX: Deprecation warning resolved
now_utc = datetime.datetime.now(timezone.utc)
log_filename = f"logs/pipeline_{now_utc.strftime('%Y%m%d')}.log"
logging.basicConfig(
   filename=log_filename,
   level=logging.INFO,
   format='%(asctime)s [%(levelname)s] %(message)s',
   datefmt='%Y-%m-%d %H:%M:%S'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)


def run_step(step_name, command, is_critical=True):
   """Executes a pipeline step in an isolated subprocess."""
   logging.info(f"--- STARTING: {step_name} ---")
   start_time = time.time()
  
   try:
       # Run the script. capture_output ensures clean console, text=True returns strings.
       result = subprocess.run(command, check=True, capture_output=True, text=True)
       elapsed = time.time() - start_time
       logging.info(f"SUCCESS: {step_name} completed in {elapsed:.2f} seconds.")
       return True, elapsed
      
   except subprocess.CalledProcessError as e:
       elapsed = time.time() - start_time
       logging.error(f"FAILED: {step_name} crashed after {elapsed:.2f} seconds.")
       logging.error(f"ERROR OUTPUT:\n{e.stderr}")
      
       if is_critical:
           logging.critical("CRITICAL STEP FAILED. HALTING PIPELINE.")
           raise SystemExit(1)
       return False, elapsed


def main():
   logging.info("=========================================")
   logging.info("STARLINK SOC PIPELINE INITIATED")
   logging.info("=========================================")
  
   pipeline_start = time.time()
   failed_steps = []
  
   # Define the sequence of pipeline steps with their respective commands and criticality
   steps = [
       ("Create Database", ["python", "database/init_db.py"], True),
       ("Data Ingestion", ["python", "-m", "ingestion.ingest_spacetrack"], True),
       ("Orbit Propagation", ["python", "-m", "propagation.propagator"], True),
       ("KD-Tree Spatial Filter", ["python", "-m", "spatial_index.candidate_pairs"], True),
       ("Conjunction Analysis", ["python", "-m", "conjunction.conjunction_analyzer"], True),
       ("SOCRATES Validation", ["python", "-m", "validation.run_validation"], False) # Non-critical
   ]
  
   # 1. Execute Pipeline Steps
   for name, cmd, critical in steps:
       success, _ = run_step(name, cmd, is_critical=critical)
       if not success:
           failed_steps.append(name)
          
   # 2. Run Health Checks
   logging.info("--- RUNNING HEALTH CHECKS ---")
   data_fresh = False
   try:
       data_fresh = health_checks.verify_tle_freshness()
       health_checks.verify_propagation_output()
       health_checks.verify_conjunction_output()
       health_checks.verify_validation_metrics()
       logging.info("All health checks passed.")
   except Exception as e:
       logging.error(f"Health Check Failure: {e}")
       failed_steps.append("Health Checks")


   # 3. Generate Daily Report & Archive
   logging.info("--- GENERATING REPORTS ---")
   total_runtime = time.time() - pipeline_start
   try:
       report_generator.generate_daily_report(
           runtime_seconds=total_runtime,
           failed_steps=failed_steps,
           data_fresh=data_fresh
       )
   except Exception as e:
       logging.error(f"Reporting Pipeline Failed: {e}")
      
   logging.info(f"PIPELINE COMPLETE. Total Runtime: {total_runtime:.2f} seconds.")
   logging.info("=========================================\n")

   print(f"To start and view the application, run: python -m visualization.app")

if __name__ == "__main__":
   main()


