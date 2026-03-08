from sqlalchemy import func
from sqlalchemy.orm import sessionmaker
from database.init_db import TLE, engine
from skyfield.api import EarthSatellite, load, wgs84
from propagation. time_grid import TimeGrid 
from propagation.coordinate_utils import validate_coordinates
import numpy as np
import pandas as pd
import os
"""
Run file:
python -m propagation.propagator
"""
HOURS = 48
STEPS_SECONDS = 60

class Propagator:

    def __init__(self):
        # Create session with database
        Session = sessionmaker(bind=engine)
        self.session = Session()
        # Load the Skyfield timescale (Need accurate time calculation)
        self.ts = load.timescale()


    def get_latest_tles(self):
       """
       Fetches the most recent TLE for every unique NORAD ID in the database.
       Returns a list of TLE objects.
       """

       print("Fetching latest TLEs from database...")

       #1. Build a subquery to find the max (latest) epoch for each satallite
       subquery = (
               self.session.query(
                   TLE.norad_id,
                   func.max(TLE.epoch).label("max_epoch")
               )
               .group_by(TLE.norad_id)
               .subquery()
       )

       # 2. Join the main TLE table with the subquery to get the full rows 
       # This ensures we only get the single newest TLE for every satellite
       query = (
           self.session.query(TLE)
           .join(subquery,
                 (TLE.norad_id == subquery.c.norad_id) &
                 (TLE.epoch == subquery.c.max_epoch))
       )

       results = query.all()

       print(f"Successfully loaded {len(results)} TLEs.")
       return results

    def create_satellite_objects(self, tles):
        """ Converts raw TLE data into Skyfield EarthSatellite objects. 
        Returns a dictionary: { norad_id: EarthSatellite_object } 
        """
        satellites = {}
        print(f"Converting {len(tles)} TLEs to Skyfield objects...")
        
        for tle in tles:
            try:
                # Create the Skyfield Objects 
                sat = EarthSatellite(tle.line1, tle.line2, tle.norad_id, self.ts)
                satellites[tle.norad_id] = sat
            except Exception as e:
                print(f"Error creating satellite {tle.norad_id}: {e}")
        
        print(f"Succesfully initalized {len(satellites)} satellite objects.")
        return satellites

    def propagate_satellites(self, satellites, time_grid, limit=None):
        """ 
        Calculates Geodetic positions (Lat, Lon, Alt) for satellites. 

        Args: 
            satellites (dict): Dictionary of Skyfield Satellite objects 
            time_grid (list): List of Python datetime objects 
            limit (int): Optional. Limit calculation to first N satellites for testing. 


        Returns: 
            dict: { norad_id: (times, positions_x, positions_y, positions_z) } 
        """
        print(f"starting propagaion for {len(time_grid)} time steps...")
        print(type(time_grid))
        # 1. Convert Python datetimes to Skyfield Time objects (Vectorized)
        t = self.ts.from_datetimes(time_grid)
        
        results = {}
        count = 0

        for norad_id, sat in satellites.items():
            if limit and count >= limit:
                break 

            try:
                # 2. The Core Math Propagate for ALL times at once
                geocentric = sat.at(t)

                # 3. Extract ECI coordinates (km)
                # position.km returns a 3xN numpy array (x, y, z rows)
                position_eci = geocentric.position.km

                # 4. Validate Coordinates
                is_valid, stats = validate_coordinates(position_eci)
                
                if is_valid == False:
                    print(f"Skipping {norad_id}: {stats['reason']}")
                    continue 

                # 5. CONVERSION: Get Latitude, Longitude, Elevation
                subpoint = wgs84.subpoint(geocentric)

                lat = subpoint.latitude.degrees
                lon = subpoint.longitude.degrees
                alt = subpoint.elevation.km

                # Store: (timestamp, x_array, y_array, z_array)
                results[norad_id] = np.vstack((lat, lon, alt))
                
                count += 1
                if count % 100 == 0:
                    print(f"Propagated {count} satellites...", end='\r')

            except Exception as e:
                print(f"Error propagating {norad_id}: {e}")

        print(f"\nPropagation complete. Compute orbits for {count} objects.")
        return results, t


    def save_results(self, results, time_grid, filename="propagation_results.parquet"):
        """
        Saves the propagation results to a Parquet file.
        
        Args:
            results (dict): { norad_id: 3xN numpy array }
            time_grid (list): List of datetime objects matching the N dimension
            filename (str): Output filename
        """
        print(f"Formatting data for {len(results)} objects...")
        
        all_frames = []
        
        # We process each satellite and turn it into a mini-table
        for norad_id, position_matrix in results.items():
            # matrix is shape (3, TimeSteps) -> Transpose to (TimeSteps, 3)
            data_transposed = position_matrix.T
            
            # Create a temporary DataFrame for this single satellite
            df = pd.DataFrame(data_transposed, columns=['latitude', 'longitude', 'altitude_km'])
            df['norad_id'] = norad_id
            df['timestamp'] = time_grid  # Assign the time column
            
            all_frames.append(df)
            
        if not all_frames:
            print("No data to save.")
            return

        # Combine all mini-tables into one massive table
        final_df = pd.concat(all_frames, ignore_index=True)
        
        # Save to disk
        print(f"Saving {len(final_df)} rows to {filename}...")
        final_df.to_parquet(filename, index=False)
        print("Save complete.")




if __name__ == '__main__':
    # --- PHASE 2 INTERGRATION TEST ---
    prop = Propagator()
    tg = TimeGrid()

    # 1. Setup Time: 2 hours, 60s steps (Small test)
    print("Step 1: generating time grid...")
    times = tg.create_time_grid(HOURS, STEPS_SECONDS)
    
    # 2. Get Data
    print("Step 2: fetching TLEs...")
    raw_tles = prop.get_latest_tles()

    # 3. Initialize
    print("Step 3: initializing satellites...")
    skyfield_sats = prop.create_satellite_objects(raw_tles)
                         
    # 4. Propagate (Add limit if you want test or remove limit for a full run)
    print("Step 4: propagating positions...")
    positions, _ = prop.propagate_satellites(skyfield_sats, times, limit=None)

    # 5. Save to disk
    print("Step 5: saving results...")
    
    save_path = "data/processed/orbit_data.parquet"
    os.makedirs(os.path.dirname(save_path), exist_ok=True) # Ensure that the folder exists

    prop.save_results(positions, times, save_path)
