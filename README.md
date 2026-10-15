# AI-Powered Smart Intersection

[Türkçe](README.tr.md)

A traffic signal simulation of a single intersection that compares three ways of running the lights under the same traffic:

1. Fixed time: every approach gets the same green in turn.
2. Adaptive, ground truth: the decision rule knows the exact number of vehicles in the camera frame.
3. Adaptive, camera: the same decision rule works only with what a YOLO11n model detects on the overhead camera frame.

The gap between 2 and 3 is what it costs to see the intersection through a camera. The gap between 1 and 2 is what the decision rule itself brings.

![Vehicle detection on the camera frame and priority for an emergency vehicle](docs/demo.gif)

## Results

22 scenarios, 10 seeds each, 10-minute runs with the first 2 minutes left out as warmup. Fixed time was run with 6, 8, 10, 12, 15 and 20 s greens, and adaptive control is compared with the best of these for each scenario. Wait time includes vehicles still queued when the run ended.

| Traffic | Camera controller vs. best fixed time |
|---|---|
| Single direction, extreme directional | 70-100% less wait |
| Sparse, idle intersection | 70-71% less wait |
| Direction-heavy, turning conflict | 55-62% less wait |
| Asymmetric peak | 28% less wait |
| 30-minute mixed scenario | 55% less wait |
| Balanced traffic | 7-16% less wait |
| Saturated peak | between 1% less and 8% more |

The camera controller beats fixed time on average in 21 of 22 scenarios. The gain is large when traffic is unbalanced or sparse, because fixed time keeps giving green to empty approaches. With balanced traffic a well-tuned fixed time is close behind. When demand exceeds capacity, reordering the greens does not help, and the longest fixed greens (15-20 s) are on par or slightly ahead.

Emergency vehicles wait 18-64 s on average with fixed time. With adaptive control it is 0.3-23 s depending on the scenario:

| Scenario | Best fixed | Ground truth | Camera |
|---|---:|---:|---:|
| Balanced traffic | 18.9 s | 1.6 s | 1.4 s |
| Right-heavy traffic | 63.6 s | 15.1 s | 12.3 s |
| Saturated peak | 50.1 s | 23.0 s | 19.9 s |
| Sparse traffic | 17.9 s | 0.3 s | 0.8 s |
| Mixed scenario | 54.6 s | 7.4 s | 8.6 s |

The difference between the camera and ground-truth controllers is between -1.0 and +1.1 s per scenario, median -0.2 s. In other words, detection errors barely change the decisions.

Full tables: `reports/baseline_sweep/summary.md` and `reports/camera/summary.md`.

## Camera pipeline

The camera controller never reads the simulation state. Its only input is the 900x900 overhead image of the intersection.

- Dataset: frames are captured from the simulation and labels are generated from the vehicle positions. 1200 training and 450 validation frames, 7 classes (car, bus, truck, bike, ambulance, police, fire truck). Validation frames come from scenarios and seeds never used in training.
- Model: YOLO11n, 896 px input, 40 epochs. On the validation set: mAP50-95 0.98, precision 0.998, recall 0.999 (`reports/detector/metrics.json`).
- Observation: the frame goes through the model once per simulated second. For each approach it yields the number of visible vehicles, whether the queue reaches the edge of the frame, and the nearest emergency vehicle if there is one.

The ground-truth controller uses the same field of view and just counts without errors. So the difference between the two comes entirely from detection errors and the one-second observation interval.

### What these results don't show

The images are the simulation's own rendering. Vehicles always have the same scale and look, and there is no lighting change, weather, shadow or occlusion. That is why the model is almost perfect, and that accuracy says nothing about a real camera. What the project does show is the whole pipeline from data generation to signal decision, and a way to measure it. The same comparison still has to be done on real footage.

Other limitations:

- A queue that spills out of the frame cannot be counted. The rule adds a few seconds of green when a queue reaches the edge as a rough correction.
- An emergency vehicle waiting outside the frame is not seen; priority starts when it enters the frame.
- One intersection, no pedestrian phase, only one approach green at a time.
- Capacity in the simulation (1.00 veh/s per approach) is about twice what was measured in real intersection recordings (0.45 veh/s). Scenarios are defined relative to capacity, so the comparison holds, but waits in seconds do not carry over directly to a real intersection. Details: `docs/scenario_capacity_calibration.md`.

## Decision rule

When a green ends, the rule looks at the observation of all four approaches:

- Approach: the one with the highest `vehicles + 1.5 × (red time beyond 20 s)` gets the green. No approach gets a second green until every approach with vehicles has had one.
- Duration: `2 s start-up + vehicles / discharge rate`, between 5 and 30 s.
- Emergency vehicle: its approach gets the next green, sized to the vehicle's arrival at the stop line. No priority is given if another approach has been red for more than 90 s.

`tools/verify_decisions.py` checks every green against what happened afterwards. With balanced traffic, the share of greens that kept running after the last vehicle had crossed is 24% with fixed time and 17% with adaptive control. With low traffic it drops from 42% to 25%. At most 3% of adaptive greens are too short, meaning not every counted vehicle got through.

Details: `docs/strategy_structure.md`.

## Architecture

![Application window: intersection and decision panel](docs/screenshot.png)

```
UI (Tkinter)  →  Controller  →  State provider  →  Simulation engine (pygame)  →  Storage (JSON)
```

- `ui/`: start a simulation, pick or edit a scenario, pick a controller. English and Turkish.
- `controllers/`: fixed-time and adaptive controllers. The adaptive controller handles the timing, `strategies/demand_strategy.py` makes the decisions.
- `state_providers/`: `ground_truth_provider.py` gives exact counts, `yolo_provider.py` gives camera detections.
- `simulation/`: spawning, motion model, signal phases, metrics and the decision panel on the right.
- `core/`, `data/`: scenarios, controller definitions and run results.

The simulation is deterministic: with the same scenario, controller and seed the result is identical, even under CPU load. `tools/verify_determinism.py` checks this.

## Setup

Python 3.10 or newer.

```bash
pip install -r requirements.txt          # pygame, matplotlib
pip install -r requirements-yolo.txt     # camera controller: ultralytics

python main.py
```

To regenerate the result tables:

```bash
python tools/baseline_sweep.py
python tools/baseline_sweep_report.py

python tools/baseline_sweep.py --greens --adaptive adaptive_camera \
    --output reports/camera/raw_results.csv
python tools/camera_comparison_report.py
```

The trained model is included as `weights/vehicle_detector.pt`. To build it from scratch:

```bash
python tools/generate_detection_dataset.py
python tools/train_detector.py
```

Checks:

```bash
python tools/verify_determinism.py     # same seed, same result
python tools/verify_vehicle_motion.py  # motion model rules
python tools/verify_decisions.py       # audit of every green
```

## Documentation

In `docs/`:

- `01_project_overview.md`: goal, architecture, experiment setup.
- `engine_overview.md`: simulation engine, motion model, determinism.
- `strategy_structure.md`: the decision rule and its parameters.
- `metrics_definitions.md`: metric definitions.
- `scenario_capacity_calibration.md`: capacity, scenario demand levels, comparison with real recordings.
- `results_and_limits.md`: full result tables and what the model does not cover.

## License

MIT, see [LICENSE](LICENSE). The Noto Sans fonts in `assets/fonts/` are under the SIL Open Font License (`assets/fonts/OFL.txt`).
