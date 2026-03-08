import numpy as np
import plotly.graph_objects as go
from skyfield.api import wgs84


def geodetic_to_ecef(lat, lon, alt_km):
   position = wgs84.latlon(lat, lon, elevation_m=alt_km * 1000)
   return position.itrs_xyz.km


def get_object_classification(norad_id, metadata):
   info = metadata.get(str(norad_id), {'name': f'UNKNOWN-{norad_id}', 'type': 'Debris/Other'})
   group_name = info['type'] 
  
   if group_name == 'Starlink':
       color = '#00FFFF'
   elif group_name == 'Spacecraft':
       color = '#00FF00'
   else:
       color = '#FFA500'
      
   return group_name, color


def get_orbit_traces(df_orbits, selected_ids, metadata):
   traces = []
   filtered_df = df_orbits[df_orbits['norad_id'].isin(selected_ids)]
   max_points_per_object = 700
  
   for norad_id, group in filtered_df.groupby('norad_id', sort=False):
       if len(group) > max_points_per_object:
           sample_idx = np.linspace(0, len(group) - 1, max_points_per_object, dtype=int)
           group = group.iloc[sample_idx]


       if {'x_km', 'y_km', 'z_km'}.issubset(group.columns):
           x = group['x_km'].values
           y = group['y_km'].values
           z = group['z_km'].values
       else:
           x, y, z = geodetic_to_ecef(group['latitude'].values, group['longitude'].values, group['altitude_km'].values)
       _, color = get_object_classification(norad_id, metadata)
      
       raw_name = metadata.get(str(norad_id), {}).get('name', f"Object {norad_id}")
       actual_name = f"{raw_name} [{norad_id}]"
      
       trace = go.Scatter3d(
           x=x, y=y, z=z,
           mode='lines',
           line=dict(color=color, width=2),
           name=actual_name,
           legendgroup=actual_name,
           hoverinfo='name',
           hoverlabel=dict(namelength=-1) # UI FIX: Forces Plotly to show the full name on hover!
       )
       traces.append(trace)
   return traces


def get_global_swarm_trace(df_orbits, metadata, show_groups):
   first_time = df_orbits['timestamp'].min()
   swarm_df = df_orbits[df_orbits['timestamp'] == first_time].copy()


   def _group_name(nid):
       return metadata.get(str(nid), {}).get('type', 'Debris/Other')


   swarm_df['group_name'] = swarm_df['norad_id'].map(_group_name)
   swarm_df['color'] = swarm_df['group_name'].map({
       'Starlink': '#00FFFF',
       'Spacecraft': '#00FF00',
       'Debris/Other': '#FFA500'
   }).fillna('#FFA500')
  
   swarm_df = swarm_df[swarm_df['group_name'].isin(show_groups)]
   if swarm_df.empty: return []


   if {'x_km', 'y_km', 'z_km'}.issubset(swarm_df.columns):
       x = swarm_df['x_km'].values
       y = swarm_df['y_km'].values
       z = swarm_df['z_km'].values
   else:
       x, y, z = geodetic_to_ecef(swarm_df['latitude'].values, swarm_df['longitude'].values, swarm_df['altitude_km'].values)
   names = swarm_df['norad_id'].astype(str).apply(lambda id: f"{metadata.get(id, {}).get('name', id)} [{id}]")
  
   trace = go.Scatter3d(
       x=x, y=y, z=z, mode='markers',
       # UI FIX: Removed opacity and reduced size to 1.0 to stop GPU freezing
       marker=dict(size=1.0, color=swarm_df['color'].tolist()),
       name='Global Swarm', hovertext=names, hoverinfo='text',
       hoverlabel=dict(namelength=-1)
   )
   return [trace]