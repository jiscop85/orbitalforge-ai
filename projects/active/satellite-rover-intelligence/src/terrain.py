from dataclasses import dataclass

import numpy as np


@dataclass
class TerrainCube:
    elevation: np.ndarray
    bands: np.ndarray
    mask: np.ndarray
    traversable: np.ndarray

    def validate(self):
        if self.elevation.ndim != 2:
            raise ValueError("elevation must be 2D")
        if self.bands.ndim != 3:
            raise ValueError("bands must be 3D")
        if self.bands.shape[:2] != self.elevation.shape:
            raise ValueError("band spatial dims mismatch")
