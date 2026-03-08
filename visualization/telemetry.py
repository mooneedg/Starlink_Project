import pandas as pd
import numpy as np
import plotly.graph_objects as go


def get_telemetry_figure(df_orbits, obj1, obj2, tca_time, metadata):
   """Generates a 2D line graph showing Distance vs. Time for two targeted objects."""
  
   # 1. Handle Empty State
   if not obj1 or not obj2:
       fig = go.Figure()
       fig.update_layout(
           paper_bgcolor='#0a0a0a', plot_bgcolor='#111111', font=dict(color='white'),
           title="Click a collision event to view Telemetry",
           xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
           yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
           margin=dict(l=0, r=0, b=0, t=40)
       )
       return fig


   # 2. Extract Data for Both Objects
   df1 = df_orbits[df_orbits['norad_id'] == str(obj1)]
   df2 = df_orbits[df_orbits['norad_id'] == str(obj2)]


   # 3. Merge on identical timestamps
   merged = pd.merge(df1, df2, on='timestamp', suffixes=('_1', '_2'))


   if merged.empty:
       fig = go.Figure()
       fig.update_layout(title="No matching time data available.", paper_bgcolor='#0a0a0a', font=dict(color='white'))
       return fig


   # 4. Calculate exact 3D Cartesian Distance in km
   if {'x_km_1', 'y_km_1', 'z_km_1', 'x_km_2', 'y_km_2', 'z_km_2'}.issubset(merged.columns):
       dx = merged['x_km_2'].to_numpy() - merged['x_km_1'].to_numpy()
       dy = merged['y_km_2'].to_numpy() - merged['y_km_1'].to_numpy()
       dz = merged['z_km_2'].to_numpy() - merged['z_km_1'].to_numpy()
       merged['distance_km'] = np.sqrt(dx**2 + dy**2 + dz**2)
   else:
       fig = go.Figure()
       fig.update_layout(title="Telemetry coordinates unavailable.", paper_bgcolor='#0a0a0a', font=dict(color='white'))
       return fig


   # 5. Trim the timeline to +/- 45 minutes around the TCA for a clean "V" shape
   if tca_time is not None:
       time_margin = pd.Timedelta(minutes=45)
       mask = (merged['timestamp'] >= tca_time - time_margin) & (merged['timestamp'] <= tca_time + time_margin)
       plot_df = merged[mask].copy()
   else:
       plot_df = merged.copy()


   if plot_df.empty:
       plot_df = merged.copy()


   # 6. Render the Plotly Graph
   name1 = f"{metadata.get(str(obj1), {}).get('name', obj1)} [{obj1}]"
   name2 = f"{metadata.get(str(obj2), {}).get('name', obj2)} [{obj2}]"
   min_dist_row = plot_df.loc[plot_df['distance_km'].idxmin()]


   fig = go.Figure()
  
   # The Telemetry Curve
   fig.add_trace(go.Scatter(
       x=plot_df['timestamp'], y=plot_df['distance_km'],
       mode='lines', name='Relative Distance',
       line=dict(color='#FFFF00', width=3)
   ))


   # The TCA Impact Point
   fig.add_trace(go.Scatter(
       x=[min_dist_row['timestamp']], y=[min_dist_row['distance_km']],
       mode='markers', name='Time of Closest Approach (TCA)',
       marker=dict(color='#FF3333', size=12, symbol='x'),
       hovertext=f"Min Distance: {min_dist_row['distance_km']:.4f} km",
       hoverinfo='x+text'
   ))


   fig.update_layout(
       title=dict(text=f"<b>Telemetry:</b> {name1} vs {name2}", font=dict(size=14)),
       xaxis_title="Time (UTC)",
       yaxis_title="Separation Distance (km)",
       paper_bgcolor='#0a0a0a', plot_bgcolor='#111111', font=dict(color='#DDDDDD'),
       margin=dict(l=80, r=50, b=55, t=50),
       legend=dict(x=0.01, y=0.99, bgcolor='rgba(0,0,0,0.5)'),
       hovermode="x unified"
   )
  
   # Add an aggressive grid to look like a control room
   fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#333333', automargin=True)
   fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#333333', zerolinecolor='#555', automargin=True, title_standoff=12)


   return fig