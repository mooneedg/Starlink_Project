import numpy as np
import plotly.graph_objects as go


def get_conjunction_markers(df_events, metadata):
   markers = []
  
   for _, event in df_events.iterrows():
       obj1 = event.get('object_1_str', str(event['object_1']))
       obj2 = event.get('object_2_str', str(event['object_2']))
      
       # Ensure name format matches the lines perfectly for grouping
       actual_name1 = f"{metadata.get(obj1, {}).get('name', f'Object {obj1}')} [{obj1}]"
       actual_name2 = f"{metadata.get(obj2, {}).get('name', f'Object {obj2}')} [{obj2}]"
              
       try:
           x1 = float(event['x1_km'])
           y1 = float(event['y1_km'])
           z1 = float(event['z1_km'])
           x2 = float(event['x2_km'])
           y2 = float(event['y2_km'])
           z2 = float(event['z2_km'])


           if np.isnan(x1) or np.isnan(y1) or np.isnan(z1) or np.isnan(x2) or np.isnan(y2) or np.isnan(z2):
               continue
          
           mid_x, mid_y, mid_z = (x1+x2)/2, (y1+y2)/2, (z1+z2)/2
          
           marker_size = np.clip(np.log1p(event['risk_score']) * 1.5, 8, 16)
           tca_str = str(event['tca_timestamp'])
           miss_dist = float(event['miss_distance_km'])
           payload = [obj1, obj2, tca_str, miss_dist, mid_x, mid_y, mid_z]
          
           # Primary Object Marker (RED)
           markers.append(go.Scatter3d(
               x=[x1], y=[y1], z=[z1],
               mode='markers',
               marker=dict(size=marker_size, color='#FF3333', symbol='circle'),
               name=f"{actual_name1} (Primary)",
               legendgroup=actual_name1, # Binds marker to line
               showlegend=False,         # Hides marker from legend text
               customdata=[payload],
               hovertext=(
                   f"<b>{actual_name1} (RED)</b><br>"
                   f"Impacting: {actual_name2} (BLUE)<br>"
                   f"Miss Distance: {miss_dist:.4f} km<br>"
                   f"TCA: {tca_str}<br><i>Click to zoom</i>"
               ),
               hoverinfo='text'
           ))


           # Secondary Object Marker (BLUE)
           markers.append(go.Scatter3d(
               x=[x2], y=[y2], z=[z2],
               mode='markers',
               marker=dict(size=marker_size, color='#3388FF', symbol='circle'),
               name=f"{actual_name2} (Secondary)",
               legendgroup=actual_name2, # Binds marker to line
               showlegend=False,         # Hides marker from legend text
               customdata=[payload],
               hovertext=(
                   f"<b>{actual_name2} (BLUE)</b><br>"
                   f"Impacting: {actual_name1} (RED)<br>"
                   f"Miss Distance: {miss_dist:.4f} km<br>"
                   f"TCA: {tca_str}<br><i>Click to zoom</i>"
               ),
               hoverinfo='text'
           ))
          
           # Impact Vector
           markers.append(go.Scatter3d(
               x=[x1, x2], y=[y1, y2], z=[z1, z2],
               mode='lines',
               line=dict(color='#FFFF00', width=4, dash='dash'),
               legendgroup=actual_name1, # Binds vector to primary
               showlegend=False,
               hoverinfo='skip'
           ))
          
       except (KeyError, ValueError, TypeError):
           continue
          
   return markers