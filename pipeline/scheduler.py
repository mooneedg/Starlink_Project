import time
import datetime
import subprocess

def run_daily_loop():
    print("Starlink SOC Scheduler Started.")
    print("Pipeline will run immediately, and then every 24 hours.")
    
    while True:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{current_time}] Triggering Daily Pipeline Execution...")
        
        # Trigger the pipeline script
        subprocess.run(["python", "-m", "pipeline.run_pipeline"])
        
        print("\nPipeline execution finished. Sleeping for 24 hours...")
        
        # Sleep for exactly 24 hours (86,400 seconds)
        time.sleep(86400)

if __name__ == "__main__":
    run_daily_loop()