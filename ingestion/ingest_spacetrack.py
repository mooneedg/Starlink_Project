import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from ingestion.update_db_groups import fetch_and_store_satcat
from utils.spacetrack_client import SpaceTrackClient

# ----------------------
# To run the script: python -m ingestion.ingest_spacetrack
# ----------------------

# ----------------------
# Configuration
# ----------------------

DB_PATH = "database/SpaceData.db"
RAW_TLE_DIR = Path("data/raw/spacetrack")
SOURCE_NAME = "space-track"

# ----------------------
# Helpers
# ----------------------

def parse_tle_epoch(line1: str) -> datetime:
    """
    Parse TLE epoch from line 1.

    Epoch format (columns 19–32):
        YYDDD.DDDDDDDD

    Where:
        YY    = last two digits of year
        DDD   = day of year
        .DDD  = fractional day
    """
    try:
        epoch_str = line1[18:32].strip()
        year = int(epoch_str[0:2])
        day_of_year = int(epoch_str[2:5]) 
        # TLE convention: years < 57 are 2000+, otherwise 1900+
        year += 2000 if year < 57 else 1900

        base_date = datetime(year,1,1) +timedelta(days = day_of_year -1)
        return base_date
    except Exception as exc:
        raise ValueError(f"Failed to parse TLE epoch from line: {line1}")
   
def parse_tle_blocks(raw_text: str):
    """
    Parse raw TLE text into (name, line1, line2) tuples.
    """
    lines = [l.rstrip() for l in raw_text.splitlines() if l.strip()]
    if len(lines) % 3 != 0:
        raise RuntimeError("Malformed TLE data: line count not divisible by 3")

    blocks = []
    for i in range(0, len(lines), 3):
        name, line1, line2 = lines[i:i + 3]

        if not (line1.startswith("1 ") and line2.startswith("2 ")):
            raise RuntimeError(f"Malformed TLE block starting at line {i}")

        blocks.append((name, line1, line2))

    return blocks

# ----------------------------
# Main Ingestion Logic
# ----------------------------

def main():
    # Load credentials
    username = os.getenv("SPACETRACK_USERNAME")
    password = os.getenv("SPACETRACK_PASSWORD")

    if not username or not password:
        raise RuntimeError("Missing Space-Track credentials in environment")

    # Authenticate and download data
    client = SpaceTrackClient(username, password)
    client.login()
    raw_tle_text = client.get_latest_tles()

    if not raw_tle_text.strip():
        raise RuntimeError("Received empty TLE response from Space-Track")

    # Save raw response to disk
    RAW_TLE_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.utcnow().strftime("%Y%m%d")
    raw_file_path = RAW_TLE_DIR / f"tle_{date_str}.txt"

    with open(raw_file_path, "w", encoding="utf-8") as f:
        f.write(raw_tle_text)

    # Parse TLEs
    tle_blocks = parse_tle_blocks(raw_tle_text)

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    ingest_time = datetime.utcnow()

    try:
        with conn:
            for object_name, line1, line2 in tle_blocks:
                # NORAD ID is columns 3–7 of line 1
                try:
                    norad_id = line1[2:7].strip()
                except ValueError as exc:
                    raise RuntimeError(f"Invalid NORAD ID in line: {line1}") from exc

                epoch = parse_tle_epoch(line1)

                # Insert or update space_objects
                cursor.execute(
                    """
                    SELECT norad_id FROM space_objects WHERE norad_id = ?
                    """,
                    (norad_id,)
                )
                exists = cursor.fetchone()

                current_obj_type = "unknown"  # Space-Track does not provide object type in this dataset

                # Check if it is a TBA object. If it is we will change the object type
                if(object_name == "0 TBA - TO BE ASSIGNED"):
                   current_obj_type = "TBA/Analyst"


                
                if exists is None:
                    cursor.execute(
                        """
                        INSERT INTO space_objects (
                            norad_id,
                            object_name,
                            object_type,
                            source,
                            first_seen,
                            last_seen
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            norad_id,
                            object_name,
                            current_obj_type,
                            SOURCE_NAME,
                            ingest_time,
                            ingest_time,
                        ),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE space_objects
                        SET last_seen = ?
                        WHERE norad_id = ?
                        """,
                        (ingest_time, norad_id),
                    )

                # Insert TLE only if this exact version does not already exist
                cursor.execute(
                    """
                    SELECT 1 FROM tles
                    WHERE norad_id = ?
                      AND line1 = ?
                      AND line2 = ?
                      AND epoch = ?
                      AND source = ?
                    """,
                    (norad_id, line1, line2, epoch, SOURCE_NAME),
                )

                if cursor.fetchone() is None:
                    cursor.execute(
                        """
                        INSERT INTO tles (
                            norad_id,
                            line1,
                            line2,
                            epoch,
                            ingest_time,
                            source
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            norad_id,
                            line1,
                            line2,
                            epoch,
                            ingest_time,
                            SOURCE_NAME,
                        ),
                    )

    finally:
        conn.close()

    # After ingesting the latest TLEs, we can fetch the SATCAT data to classify the objects we just ingested
    fetch_and_store_satcat(DB_PATH)
    
if __name__ == "__main__":
    main()
