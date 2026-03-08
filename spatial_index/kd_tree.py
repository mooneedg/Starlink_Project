import numpy as np
from scipy.spatial import cKDTree

class SpatialIndex:
    """
    Wrapper for Scipy's cKDTree to perform efficient spatial queries 
    on 3D point clouds.
    """

    def __init__(self, coordinates):
        """
        Builds the KD-Tree from a (N, 3) numpy array of positions.
        
        Args:
            coordinates (np.array): Shape (N, 3) array of x, y, z positions.
        """
        # data needs to be clean float numbers
        self.data = np.asarray(coordinates, dtype=np.float64)
        self.tree = cKDTree(self.data)

    def query_pairs(self, radius_km):
        """
        Finds all unique pairs of points within the specified radius.
        
        Args:
            radius_km (float): The search radius in kilometers.
            
        Returns:
            set: A set of tuples (index_i, index_j) where index_i < index_j.
                 Indices correspond to the row numbers of the input coordinates.
        """
        # query_pairs returns a set of (i, j) where i < j and dist(i, j) < r
        # This automatically handles the "No duplicate pairs" and "No self-matches" rules.
        return self.tree.query_pairs(r=radius_km)

