# Build status — Satellite-to-Rover Terrain Intelligence

**Phase:** `build`

- [ ] **T01 — Scientific data model and terrain simulator**
- [ ] **T02 — Remote-sensing preprocessing and features**
- [ ] **T03 — Baseline traversability model**
- [ ] **T04 — Uncertainty-aware spatial risk map**
- [ ] **T05 — Rover cost-grid model**
- [ ] **T06 — Risk-aware A-star planner**
- [ ] **T07 — Dynamic hazard replanning**
- [ ] **T08 — Rover state estimation**
- [ ] **T09 — Integrated mission simulator**
- [ ] **T10 — Experiment harness and documentation**

## Current automated review guidance

Previous attempt was rolled back by automated validation: /opt/hostedtoolcache/Python/3.12.14/x64/bin/python -m ruff format --check /tmp/orbitalforge-96vt9ov5/project/src failed (1):
unformatted: File would be reformatted
  --> src/terrain.py:64:25
   |
63 |     traversability = np.where(mask, np.clip(elevation, 0.0, 1.0), 0.0)
   -     return TerrainScene(bands=bands, elevation=elevation, mask=mask, traversability=traversability)
64 +     return TerrainScene(
65 +         bands=bands, elevation=elevation, mask=mask, traversability=traversability
66 +     )
   |

1 file would be reformatted


> Progress advances only after security, quality, test, and review gates.
