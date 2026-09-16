# Project specification

```json
{
  "id": "satellite-rover-intelligence",
  "title": "Satellite-to-Rover Terrain Intelligence",
  "summary": "Build a reproducible pipeline that turns synthetic multispectral satellite terrain observations into uncertainty-aware traversability maps and uses them for simulated rover planning, state estimation, and mission evaluation.",
  "domains": [
    "AI/ML",
    "robotics",
    "data processing",
    "satellite systems",
    "remote sensing"
  ],
  "tasks": [
    {
      "id": "T01",
      "title": "Scientific data model and terrain simulator",
      "instruction": "Create typed terrain-cube structures and a deterministic multispectral/elevation simulator with obstacles and ground-truth traversability.",
      "acceptance_criteria": [
        "Same seed produces identical scenes and different seeds can produce different scenes.",
        "Band shapes, masks, elevation and traversability are validated with explicit invariants.",
        "Tests cover invalid dimensions/ranges and reproducibility."
      ]
    },
    {
      "id": "T02",
      "title": "Remote-sensing preprocessing and features",
      "instruction": "Implement missing-data handling, normalization, spectral indices, slope and roughness features for the synthetic cube.",
      "acceptance_criteria": [
        "Invalid/cloud-like pixels are represented explicitly rather than silently imputed.",
        "Feature names/shapes are deterministic and documented.",
        "Tests include constant bands, missing values and boundary terrain."
      ]
    },
    {
      "id": "T03",
      "title": "Baseline traversability model",
      "instruction": "Implement a reproducible classical ML baseline for traversability/risk prediction with train/evaluation separation.",
      "acceptance_criteria": [
        "Training and evaluation use deterministic splits without leakage.",
        "Metrics are computed from actual predictions and never hard-coded.",
        "Tests validate probability/risk bounds and degenerate inputs."
      ]
    },
    {
      "id": "T04",
      "title": "Uncertainty-aware spatial risk map",
      "instruction": "Add spatial post-processing and uncertainty estimation without smoothing across hard obstacle boundaries.",
      "acceptance_criteria": [
        "Risk and uncertainty outputs are bounded and shape-preserving.",
        "Obstacles remain impassable after post-processing.",
        "Tests cover small maps, edges and high-uncertainty regions."
      ]
    },
    {
      "id": "T05",
      "title": "Rover cost-grid model",
      "instruction": "Convert risk, elevation and uncertainty into an explicit navigation cost grid.",
      "acceptance_criteria": [
        "Impassable cells use a documented representation.",
        "Cost components and weights are validated and non-negative.",
        "Tests verify monotonicity: increased risk/uncertainty cannot lower cost."
      ]
    },
    {
      "id": "T06",
      "title": "Risk-aware A-star planner",
      "instruction": "Implement deterministic 8-connected A-star route planning over the cost grid.",
      "acceptance_criteria": [
        "Planner returns valid adjacent paths or a clear unreachable result.",
        "Path cost matches the documented movement/cell-cost model.",
        "Tests cover start=goal, blocked goals and competing safe/risky routes."
      ]
    },
    {
      "id": "T07",
      "title": "Dynamic hazard replanning",
      "instruction": "Simulate newly discovered local hazards and route replanning during execution.",
      "acceptance_criteria": [
        "Simulation never traverses a newly marked impassable cell.",
        "Metrics include route length, accumulated risk and replanning count from actual execution.",
        "Tests are deterministic under a fixed seed."
      ]
    },
    {
      "id": "T08",
      "title": "Rover state estimation",
      "instruction": "Implement a lightweight 2D Kalman-style estimator for simulated odometry and GNSS-like observations.",
      "acceptance_criteria": [
        "Prediction/update dimensions and covariance properties are checked.",
        "Estimator handles missing observations explicitly.",
        "Tests verify covariance symmetry/non-negative diagonals and deterministic replay."
      ]
    },
    {
      "id": "T09",
      "title": "Integrated mission simulator",
      "instruction": "Connect terrain generation, risk modeling, planning, state estimation and execution into one offline mission demo.",
      "acceptance_criteria": [
        "A single seeded entry point runs end-to-end without network access.",
        "Machine-readable mission metrics are emitted from the actual run.",
        "Integration tests cover both reachable and unreachable missions."
      ]
    },
    {
      "id": "T10",
      "title": "Experiment harness and documentation",
      "instruction": "Add multi-seed experiments, CSV/JSON results and complete architecture/assumptions/limitations documentation.",
      "acceptance_criteria": [
        "Repeated experiment batches are reproducible.",
        "Documentation explains synthetic-data limitations and does not claim real-world performance.",
        "README contains a concrete offline usage example and interprets metrics correctly."
      ]
    }
  ]
}
```
