import pandas as pd
import sqlite3


def fetch_and_store_satcat(db_path="database/SpaceData.db"):
   """
   Downloads the official DoD SATCAT from CelesTrak and populates
   the object_groups table using the correct CelesTrak abbreviation codes.
   """
   print("\n--- Fetching Official SATCAT Data ---")
   url = "https://celestrak.org/pub/satcat.csv"
  
   try:
       print(f"Downloading {url}...")
       satcat_df = pd.read_csv(url)
      
       conn = sqlite3.connect(db_path)
       cursor = conn.cursor()
      
       cursor.execute('''
           CREATE TABLE IF NOT EXISTS object_groups (
               norad_id TEXT PRIMARY KEY,
               group_name TEXT,
               source TEXT
           )
       ''')
      
       cursor.execute("DELETE FROM object_groups")
      
       existing_ids_df = pd.read_sql("SELECT norad_id FROM space_objects", conn)
       tracked_ids = existing_ids_df['norad_id'].astype(str).unique()
      
       satcat_df['NORAD_CAT_ID'] = satcat_df['NORAD_CAT_ID'].astype(str)
       filtered_satcat = satcat_df[satcat_df['NORAD_CAT_ID'].isin(tracked_ids)].copy()
      
       def classify_object(row):
           name = str(row['OBJECT_NAME']).strip().upper()
           obj_type = str(row['OBJECT_TYPE']).strip().upper()
          
           if 'STARLINK' in name:
               return 'Starlink'
           # THE FIX: Look for the exact abbreviation 'PAY'
           elif obj_type == 'PAY':
               return 'Spacecraft'
           else: 
               return 'Debris/Other'
              
       filtered_satcat['group_name'] = filtered_satcat.apply(classify_object, axis=1)
       filtered_satcat['source'] = 'DoD SATCAT'
      
       insert_data = filtered_satcat[['NORAD_CAT_ID', 'group_name', 'source']].rename(
           columns={'NORAD_CAT_ID': 'norad_id'}
       )
      
       insert_data.to_sql('object_groups', conn, if_exists='append', index=False)
       print(f"Successfully classified {len(insert_data)} objects in the 'object_groups' table.")
      
   except Exception as e:
       print(f"Error fetching/updating SATCAT data: {e}")
   finally:
       if 'conn' in locals():
           conn.commit()
           conn.close()
