import dash
from dash import Input, Output, State, ctx
import plotly.graph_objects as go
import pandas as pd
import sqlite3
import os
import numpy as np
import sys
from functools import lru_cache


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
   sys.path.insert(0, PROJECT_ROOT)


from visualization.earth import get_earth_mesh
from visualization.orbits import get_orbit_traces, get_global_swarm_trace, geodetic_to_ecef
from visualization.conjunction_markers import get_conjunction_markers
from visualization.layout import create_layout
from visualization.telemetry import get_telemetry_figure


ORBIT_FILE = "data/processed/orbit_data.parquet"
EVENTS_FILE = "data/processed/conjunction_events.parquet"
DB_FILE = "database/SpaceData.db"


if not os.path.exists(ORBIT_FILE) or not os.path.exists(EVENTS_FILE):
   raise FileNotFoundError("Missing Parquet files. Please run Phase 2 and Phase 4 first.")


metadata = {}
try:
   if os.path.exists(DB_FILE):
       conn = sqlite3.connect(DB_FILE)
       cursor = conn.cursor()
       query = """
           SELECT s.norad_id, s.object_name, COALESCE(g.group_name, 'Debris/Other') as group_name
           FROM space_objects s
           LEFT JOIN object_groups g ON s.norad_id = g.norad_id
       """
       cursor.execute(query)
       for row in cursor.fetchall():
           metadata[str(row[0])] = {'name': row[1], 'type': row[2]}
       conn.close()
except Exception as e:
   print(f"Database error: {e}")


df_orbits = pd.read_parquet(ORBIT_FILE)
df_events = pd.read_parquet(EVENTS_FILE)


df_orbits['norad_id'] = df_orbits['norad_id'].astype(str)
df_orbits['timestamp'] = pd.to_datetime(df_orbits['timestamp'], utc=True)


x_km, y_km, z_km = geodetic_to_ecef(
   df_orbits['latitude'].to_numpy(),
   df_orbits['longitude'].to_numpy(),
   df_orbits['altitude_km'].to_numpy()
)
df_orbits['x_km'] = x_km
df_orbits['y_km'] = y_km
df_orbits['z_km'] = z_km


orbit_lookup = df_orbits.set_index(['norad_id', 'timestamp']).sort_index()
orbits_by_id = {norad_id: grp.sort_values('timestamp') for norad_id, grp in df_orbits.groupby('norad_id', sort=False)}
first_orbit_timestamp = df_orbits['timestamp'].min()
all_ids = df_orbits['norad_id'].unique()
catalog_records = []
catalog_by_value = {}
for nid in all_ids:
   nid_str = str(nid)
   name = metadata.get(nid_str, {}).get('name', nid_str)
   label = f"{name} ({nid_str})"
   rec = {
       'value': nid_str,
       'name': name,
       'name_lower': str(name).lower(),
       'label': label
   }
   catalog_records.append(rec)
   catalog_by_value[nid_str] = rec


df_events['tca_timestamp'] = pd.to_datetime(df_events['tca_timestamp'], utc=True)
df_events['reference_timestamp'] = pd.to_datetime(df_events['reference_timestamp'], utc=True)
df_events['object_1_str'] = df_events['object_1'].astype(str)
df_events['object_2_str'] = df_events['object_2'].astype(str)
df_events['obj1_clean'] = df_events['object_1_str'].str.lstrip('0')
df_events['obj2_clean'] = df_events['object_2_str'].str.lstrip('0')


group_map = {obj_id: info.get('type', 'Debris/Other') for obj_id, info in metadata.items()}
df_events['group_1'] = df_events['object_1_str'].map(group_map).fillna('Debris/Other')
df_events['group_2'] = df_events['object_2_str'].map(group_map).fillna('Debris/Other')
df_events['involves_starlink'] = (df_events['group_1'] == 'Starlink') | (df_events['group_2'] == 'Starlink')


orbit_positions = df_orbits[['norad_id', 'timestamp', 'x_km', 'y_km', 'z_km']].copy()
obj1_positions = orbit_positions.rename(columns={
   'norad_id': 'object_1_str',
   'timestamp': 'reference_timestamp',
   'x_km': 'x1_km',
   'y_km': 'y1_km',
   'z_km': 'z1_km'
})
obj2_positions = orbit_positions.rename(columns={
   'norad_id': 'object_2_str',
   'timestamp': 'reference_timestamp',
   'x_km': 'x2_km',
   'y_km': 'y2_km',
   'z_km': 'z2_km'
})
df_events = df_events.merge(obj1_positions, how='left', on=['object_1_str', 'reference_timestamp'])
df_events = df_events.merge(obj2_positions, how='left', on=['object_2_str', 'reference_timestamp'])


min_date = df_events['tca_timestamp'].min().date()
max_date = df_events['tca_timestamp'].max().date()


app = dash.Dash(__name__)
app.title = "Collision Avoidance Dashboard"
app.layout = create_layout(all_ids, min_date, max_date, metadata)




@app.callback(
   Output('sat-dropdown', 'options'),
   Input('sat-dropdown', 'search_value'),
   State('sat-dropdown', 'value')
)
def update_sat_dropdown_options(search_value, selected_values):
   selected_values = selected_values or []
   selected_set = set(selected_values)


   selected_options = []
   for value in selected_values:
       rec = catalog_by_value.get(str(value))
       if rec:
           selected_options.append({'label': rec['label'], 'value': rec['value']})


   if not search_value or not str(search_value).strip():
       return selected_options


   query = str(search_value).strip().lower()
   matches = []
   for rec in catalog_records:
       if rec['value'] in selected_set:
           continue
       if query in rec['value'] or query in rec['name_lower']:
           matches.append({'label': rec['label'], 'value': rec['value']})
           if len(matches) >= 60:
               break


   return selected_options + matches




def get_orbit_slice_for_ids(target_ids, start_time, end_time):
   frames = []
   for target_id in target_ids:
       obj_df = orbits_by_id.get(target_id)
       if obj_df is None:
           continue
       window = obj_df[(obj_df['timestamp'] >= start_time) & (obj_df['timestamp'] <= end_time)]
       if not window.empty:
           frames.append(window)
   return pd.concat(frames, ignore_index=False) if frames else df_orbits.head(0)




@lru_cache(maxsize=256)
def get_top_event_indices_cached(show_groups_key, min_dist_key, ghost_hide, starlink_only, unique_only, top_n, start_date_key, end_date_key):
   start_ts = pd.to_datetime(start_date_key, utc=True)
   end_ts = pd.to_datetime(end_date_key, utc=True) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)


   filtered = df_events[(df_events['tca_timestamp'] >= start_ts) & (df_events['tca_timestamp'] <= end_ts)]


   if min_dist_key is not None:
       filtered = filtered[filtered['miss_distance_km'] >= min_dist_key]


   if ghost_hide:
       filtered = filtered[filtered['obj1_clean'] != filtered['obj2_clean']]


   if not filtered.empty:
       filtered = filtered[
           filtered['group_1'].isin(show_groups_key) &
           filtered['group_2'].isin(show_groups_key)
       ]
       if starlink_only:
           filtered = filtered[filtered['involves_starlink']]


   if unique_only and not filtered.empty:
       filtered = filtered.sort_values(by='risk_score', ascending=False)
       seen_objects = set()
       keep_index = []
       for row in filtered.itertuples(index=True):
           o1 = row.object_1_str
           o2 = row.object_2_str
           if o1 not in seen_objects and o2 not in seen_objects:
               keep_index.append(row.Index)
               seen_objects.add(o1)
               seen_objects.add(o2)
       filtered = filtered.loc[keep_index] if keep_index else filtered.iloc[0:0]


   top_events = filtered.sort_values(by='risk_score', ascending=False).head(top_n)
   return tuple(top_events.index.tolist())


@app.callback(
   [Output('orbit-graph', 'figure'),
    Output('sat-dropdown', 'value'),
    Output('telemetry-dropdown', 'options'),
    Output('telemetry-dropdown', 'value')],
   [Input('group-checklist', 'value'),
    Input('min-dist-filter', 'value'), 
    Input('ghost-filter', 'value'),
    Input('starlink-focus-filter', 'value'),
    Input('unique-event-filter', 'value'),
    Input('targeting-radio', 'value'),
    Input('track-length-input', 'value'),
    Input('swarm-radio', 'value'),
    Input('risk-slider', 'value'),
    Input('date-picker', 'start_date'),   # UI FIX: Listen for unified start date
    Input('date-picker', 'end_date'),     # UI FIX: Listen for unified end date
    Input('sat-dropdown', 'value'),
    Input('orbit-graph', 'clickData'),
    Input('reset-btn', 'n_clicks'),
    Input('drag-mode', 'value'),
    Input('zoom-lock', 'value')]
)


def update_main_dashboard(show_groups, min_dist, ghost_filter, starlink_focus, unique_event, targeting_mode, track_length, swarm_mode, top_n, start_date, end_date, manual_sats, click_data, reset_clicks, drag_mode, zoom_lock):
  
   triggered = ctx.triggered_id
   if manual_sats is None: manual_sats = []
      
   tca_focus_time = None
   zoom_override = None
   hide_earth = False
   clicked_telemetry_val = None
  
   if triggered == 'reset-btn': manual_sats = []
      
   if triggered == 'orbit-graph' and click_data:
       points = click_data.get('points', [])
       if points and 'customdata' in points[0]:
           clicked_data = points[0]['customdata']
           manual_sats = [str(clicked_data[0]), str(clicked_data[1])]
           tca_focus_time = pd.to_datetime(clicked_data[2], utc=True)
           miss_dist = float(clicked_data[3])
          
           mid_x, mid_y, mid_z = float(clicked_data[4]), float(clicked_data[5]), float(clicked_data[6])
           box = max(miss_dist * 3.0, 1.5)
           hide_earth = True
           zoom_override = {'x': [mid_x - box, mid_x + box], 'y': [mid_y - box, mid_y + box], 'z': [mid_z - box, mid_z + box]}
           clicked_telemetry_val = f"{clicked_data[0]}___{clicked_data[1]}___{clicked_data[2]}"
          
   show_groups_key = tuple(sorted(show_groups or []))
   min_dist_key = float(min_dist) if min_dist is not None else None
   ghost_hide = bool(ghost_filter and 'hide' in ghost_filter)
   starlink_only = bool(starlink_focus and 'focus' in starlink_focus)
   unique_only = bool(unique_event and 'unique' in unique_event)


   top_idx = get_top_event_indices_cached(
       show_groups_key,
       min_dist_key,
       ghost_hide,
       starlink_only,
       unique_only,
       int(top_n),
       str(start_date),
       str(end_date)
   )
   top_events = df_events.loc[list(top_idx)] if top_idx else df_events.iloc[0:0]
  
   tel_options = []
   for _, row in top_events.iterrows():
       o1, o2 = row['object_1_str'], row['object_2_str']
       n1 = metadata.get(o1, {}).get('name', o1)
       n2 = metadata.get(o2, {}).get('name', o2)
       tca_clean = pd.to_datetime(row['tca_timestamp']).strftime('%Y-%m-%d %H:%M')
       lbl = f"TCA {tca_clean} | {n1} vs {n2} ({row['miss_distance_km']:.2f} km)"
       val = f"{o1}___{o2}___{row['tca_timestamp']}"
       tel_options.append({'label': lbl, 'value': val})


   tel_value = clicked_telemetry_val if clicked_telemetry_val else (tel_options[0]['value'] if tel_options else None)
  
   traces = []
   if not hide_earth: traces.append(get_earth_mesh())
   if swarm_mode == 'on': traces.extend(get_global_swarm_trace(df_orbits, metadata, show_groups))
  
   if track_length is None or track_length < 0:
       track_length = 0
   time_margin = pd.Timedelta(minutes=track_length)


   if manual_sats:
       if tca_focus_time is not None:
           mask = (df_orbits['timestamp'] >= tca_focus_time - time_margin) & (df_orbits['timestamp'] <= tca_focus_time + time_margin)
           local_orbits = df_orbits[mask]
          
           if track_length > 0:
               traces.extend(get_orbit_traces(local_orbits, manual_sats, metadata))
          
           local_events = top_events[(top_events['object_1_str'].isin(manual_sats)) & (top_events['object_2_str'].isin(manual_sats))]
           traces.extend(get_conjunction_markers(local_events, metadata))
       else:
           mask = df_orbits['timestamp'] <= (first_orbit_timestamp + time_margin * 2)
           local_orbits = df_orbits[mask]
          
           if track_length > 0:
               traces.extend(get_orbit_traces(local_orbits, manual_sats, metadata))
          
           local_events = top_events[top_events['object_1_str'].isin(manual_sats) | top_events['object_2_str'].isin(manual_sats)]
           traces.extend(get_conjunction_markers(local_events, metadata))
      
   else:
       if not top_events.empty:
           if targeting_mode == 'single':
               event = top_events.iloc[0]
               target_ids = [event['object_1_str'], event['object_2_str']]
               tca_time = pd.to_datetime(event['tca_timestamp'])
               local_orbits = get_orbit_slice_for_ids(target_ids, tca_time - time_margin, tca_time + time_margin)
              
               if track_length > 0:
                   traces.extend(get_orbit_traces(local_orbits, target_ids, metadata))
                  
               traces.extend(get_conjunction_markers(top_events.head(1), metadata))
           else:
               if track_length > 0:
                   id_windows = {}
                   for _, row in top_events.iterrows():
                       t = pd.to_datetime(row['tca_timestamp'])
                       o1, o2 = row['object_1_str'], row['object_2_str']
                       t_start = t - time_margin
                       t_end = t + time_margin


                       prev1 = id_windows.get(o1)
                       prev2 = id_windows.get(o2)
                       id_windows[o1] = (min(prev1[0], t_start), max(prev1[1], t_end)) if prev1 else (t_start, t_end)
                       id_windows[o2] = (min(prev2[0], t_start), max(prev2[1], t_end)) if prev2 else (t_start, t_end)
                  
                   local_orbits_list = []
                   for object_id, (w_start, w_end) in id_windows.items():
                       obj_df = orbits_by_id.get(object_id)
                       if obj_df is None:
                           continue
                       window = obj_df[(obj_df['timestamp'] >= w_start) & (obj_df['timestamp'] <= w_end)]
                       if not window.empty:
                           local_orbits_list.append(window)


                   local_orbits = pd.concat(local_orbits_list, ignore_index=False).drop_duplicates() if local_orbits_list else df_orbits.head(0)
                   target_ids = list(id_windows.keys())
                   traces.extend(get_orbit_traces(local_orbits, target_ids, metadata))
                  
               traces.extend(get_conjunction_markers(top_events, metadata))
  
   scene_layout = dict(
       xaxis=dict(visible=False, showbackground=False), yaxis=dict(visible=False, showbackground=False), zaxis=dict(visible=False, showbackground=False),
       bgcolor='black', dragmode=drag_mode, aspectmode='cube'
   )
  
   if zoom_override:
       scene_layout['xaxis']['range'] = zoom_override['x']
       scene_layout['yaxis']['range'] = zoom_override['y']
       scene_layout['zaxis']['range'] = zoom_override['z']
       scene_layout['camera'] = dict(up=dict(x=0, y=0, z=1), center=dict(x=0, y=0, z=0), eye=dict(x=1.0, y=1.0, z=0.5))
   else:
       scene_layout['camera'] = dict(up=dict(x=0, y=0, z=1), center=dict(x=0, y=0, z=0), eye=dict(x=1.5, y=1.5, z=1.5))
       if zoom_lock == 'leo':
           scene_layout['xaxis']['range'] = [-10000, 10000]
           scene_layout['yaxis']['range'] = [-10000, 10000]
           scene_layout['zaxis']['range'] = [-10000, 10000]


   # UI FIX: Add the reset_clicks counter to the base view so the camera is forced to reset!
   safe_clicks = reset_clicks if reset_clicks else 0
   ui_rev = f"locked_view_{safe_clicks}" if not zoom_override else f"zoom_{tca_focus_time}"


   fig = go.Figure(data=traces)
   fig.update_layout(
       uirevision=ui_rev,
       scene=scene_layout, paper_bgcolor='black', plot_bgcolor='black', margin=dict(l=0, r=0, b=0, t=0),
       showlegend=True, legend=dict(font=dict(color="white"), x=0, y=1)
   )
  
   return fig, manual_sats, tel_options, tel_value


@app.callback(Output('telemetry-graph', 'figure'), Input('telemetry-dropdown', 'value'))
def update_telemetry(selected_event):
   if not selected_event:
       fig = go.Figure()
       fig.update_layout(paper_bgcolor='#0a0a0a', plot_bgcolor='#111111', font=dict(color='white'), title="No event selected for telemetry.", margin=dict(l=0, r=0, b=0, t=40))
       return fig
      
   parts = selected_event.split('___')
   if len(parts) == 3:
       return get_telemetry_figure(df_orbits, parts[0], parts[1], pd.to_datetime(parts[2], utc=True), metadata)
   return go.Figure()


# --- NEW CALLBACKS: COLLAPSIBLE PANELS ---
@app.callback(
   Output('sidebar-container', 'style'),
   Input('toggle-sidebar-btn', 'n_clicks')
)
def toggle_sidebar(n):
   # Default styling for the sidebar
   base_style = {
       'width': '340px', 'minWidth': '340px', 'backgroundColor': '#12161F',
       'borderRight': '1px solid #222631', 'display': 'flex', 'flexDirection': 'column',
       'boxShadow': '2px 0 10px rgba(0,0,0,0.3)', 'zIndex': '10'
   }
   # If clicked an odd number of times, hide it
   if n and n % 2 == 1:
       base_style['display'] = 'none'
   return base_style


@app.callback(
   Output('telemetry-container', 'style'),
   Input('toggle-telemetry-btn', 'n_clicks')
)
def toggle_telemetry(n):
   # UI FIX: Changed 'minHeight' from '250px' to '0'
   base_style = {
       'flex': '4', 'minHeight': '0', 'display': 'flex', 'flexDirection': 'column',
       'borderTop': '2px solid #00E5FF', 'backgroundColor': '#12161F'
   }
   if n and n % 2 == 1:
       base_style['display'] = 'none'
   return base_style


def run_dashboard():
   print("\n--- LAUNCHING STARLINK COLLISION DASHBOARD ---")
   app.run(debug=True, use_reloader=False)


if __name__ == "__main__":
   run_dashboard()

