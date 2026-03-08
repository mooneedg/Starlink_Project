import numpy as np
import plotly.graph_objects as go


def get_earth_mesh():
   """
   Generates a 3D sphere representing the Earth.
   Radius = 6371 km.
   """
   R = 6371.0
  
   # Create mesh grid for sphere
   theta = np.linspace(0, 2 * np.pi, 100)
   phi = np.linspace(0, np.pi, 100)
  
   x = R * np.outer(np.cos(theta), np.sin(phi))
   y = R * np.outer(np.sin(theta), np.sin(phi))
   z = R * np.outer(np.ones(100), np.cos(phi))
  
   earth_surface = go.Surface(
       x=x, y=y, z=z,
       colorscale='Blues',
       showscale=False,
       opacity=0.3,
       hoverinfo='skip',
       name='Earth'
   )
  
   return earth_surface