# AI-Powered Smart Intersection: Project Overview

## Goal

Three ways of running the lights at a single intersection are compared on the same scenarios:

1. Fixed time: every approach gets the same green in turn.
2. Adaptive, ground truth: the decision rule works with the exact number of vehicles in the camera frame.
3. Adaptive, camera: the same decision rule works only with YOLO11n detections.

The gap between 2 and 3 is what it costs to see the intersection through a camera.

## Architecture

```
UI (Tkinter)  →  Controller  →  State provider  →  Simulation engine  →  Storage (JSON)
```

- UI (`ui/`): start a simulation, pick or edit a scenario, pick a controller.
- Controller (`controllers/`): `fixed_time_controller.py` or `adaptive_controller.py`. The adaptive controller handles the timing, `strategies/demand_strategy.py` makes the decisions. See `docs/strategy_structure.md`.
- State provider (`state_providers/`): `ground_truth_provider.py` gives the exact count, `yolo_provider.py` the detections on the camera frame. Both use the same field of view.
- Simulation engine (`simulation/`): spawning, vehicle motion, signal phases, metrics, side panel. See `docs/engine_overview.md`.
- Storage (`core/`, `data/*.json`): scenarios, controller definitions and run results.

## Scenarios and experiment setup

`data/scenarios.json` holds 22 scenarios: balanced, direction-heavy, peak, sparse, demand that changes during the run, scenarios with emergency vehicles, and the 30-minute `mixed_master_scenario` that plays all of them back to back. How the demand levels were set is in `docs/scenario_capacity_calibration.md`.

A run is defined by scenario, controller and seed, and with those fixed the result is identical every time. The result tables come from `tools/baseline_sweep.py`: 10 seeds per scenario, 10-minute runs, the first 2 minutes as warmup. Fixed time is swept over six green durations and the adaptive controllers are compared with the best one for each scenario.

## Documents

- `docs/engine_overview.md`: how the engine works, motion model, determinism.
- `docs/strategy_structure.md`: the decision rule and its parameters.
- `docs/metrics_definitions.md`: metric definitions.
- `docs/scenario_capacity_calibration.md`: capacity measurement, scenario demand levels, comparison with real recordings.
- `docs/results_and_limits.md`: full result tables and what the model does not cover.
