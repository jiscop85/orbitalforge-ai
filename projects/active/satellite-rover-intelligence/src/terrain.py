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
        if self.mask.shape != self.elevation.shape:
            raise ValueError("mask shape mismatch")
        if self.traversable.shape != self.elevation.shape:
            raise ValueError("traversable shape mismatch")
        if not np.all((self.mask >= 0) & (self.mask <= 1)):
            raise ValueError("mask out of range")
        if not np.all((self.traversable >= 0) & (self.traversable <= 1)):
            raise ValueError("traversable out of range")


def simulate_terrain(size: int, seed: int) -> TerrainCube:
    if size < 1:
        raise ValueError("size must be positive")
    rng = np.random.default_rng(seed)
    elev = rng.uniform(0.0, 100.0, (size, size))
    bands = rng.uniform(0.0, 1.0, (size, size, 4))
    mask = np.ones((size, size), dtype=float)
    traversable = np.ones((size, size), dtype=float)
    n_obs = max(1, size // 8)
    for _ in range(n_obs):
        r, c = rng.integers(0, size, 2)
        mask[r, c] = 0.0
        traversable[r, c] = 0.0
    cube = TerrainCube(elevation=elev, bands=bands, mask=mask, traversable=traversable)
    cube.validate()
    return cube
