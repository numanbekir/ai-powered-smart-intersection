# Results and Limitations

Full result tables for the three controllers on all 22 scenarios, and what the simulation simplifies compared with a real intersection.

## Method

- Each run is 600 s, the first 120 s are warmup. `mixed_master_scenario` runs for its own length (1800 s).
- 10 seeds per scenario, 3 for `mixed_master_scenario`.
- Fixed time is run separately with 6, 8, 10, 12, 15 and 20 s greens, and the adaptive controllers are compared with the best of these for each scenario. Comparing against a single fixed time would flatter adaptive control, because the best fixed time ranges from 6 to 20 s depending on the scenario.
- Wait covers every measured vehicle: those that crossed and those still queued when the run ended (see `docs/metrics_definitions.md`).
- All controllers run on the same scenarios and seeds. Spawning does not depend on the controller, so every controller sees exactly the same traffic.

Raw data is in `reports/baseline_sweep/raw_results.csv` and `reports/camera/raw_results.csv`. The summaries are produced by `tools/baseline_sweep_report.py` and `tools/camera_comparison_report.py`.

## Ground-truth adaptive vs. fixed time

- Gain over each scenario's best fixed time: median 22%, mean 35%, lowest -7%.
- Adaptive is ahead on average in 20 of 22 scenarios, and ahead in at least 80% of runs in 18.
- Gain over the default fixed time (10 s) is 40% on average. This number should not be quoted on its own, for the reason above.

Average wait (s):

| Scenario | fixed 6s | fixed 8s | fixed 10s | fixed 12s | fixed 15s | fixed 20s | best fixed | best adaptive | gain (fixed 10s) | gain (best fixed) | adaptive ahead (runs) | not crossed: fixed / adaptive |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| balanced_traffic | 25.2 | 21.4 | 22.4 | 23.4 | 25.9 | 30.6 | 8s | 19.9 | 11% | 7% | 6/10 | 7% / 6% |
| right_heavy_traffic | 52.6 | 52.6 | 53.8 | 51.9 | 55.9 | 56.9 | 12s | 21.5 | 60% | 59% | 10/10 | 24% / 8% |
| vertical_heavy_traffic | 54.6 | 46.6 | 42.4 | 41.6 | 40.0 | 42.1 | 15s | 18.2 | 57% | 55% | 10/10 | 15% / 5% |
| peak_traffic | 66.4 | 54.8 | 48.9 | 44.4 | 43.0 | 42.6 | 20s | 42.6 | 13% | -0% | 5/10 | 14% / 16% |
| low_traffic | 14.6 | 15.9 | 17.7 | 20.6 | 23.6 | 28.6 | 6s | 12.5 | 29% | 15% | 10/10 | 4% / 4% |
| turn_heavy_traffic | 27.6 | 23.4 | 23.5 | 24.3 | 26.6 | 30.9 | 8s | 20.8 | 11% | 11% | 8/10 | 7% / 6% |
| single_direction_traffic | 39.3 | 52.3 | 64.3 | 72.8 | 87.6 | 108.7 | 6s | 0.0 | 100% | 100% | 10/10 | 91% / 1% |
| extreme_directional_traffic | 55.8 | 67.7 | 77.1 | 82.6 | 91.4 | 101.4 | 6s | 17.5 | 77% | 69% | 10/10 | 67% / 10% |
| sparse_traffic | 13.9 | 15.3 | 16.8 | 19.2 | 22.4 | 28.3 | 6s | 4.0 | 76% | 71% | 10/10 | 5% / 2% |
| idle_intersection | 12.3 | 13.4 | 16.6 | 18.3 | 23.4 | 25.9 | 6s | 3.6 | 79% | 71% | 10/10 | 4% / 3% |
| direction_shift_traffic | 28.7 | 23.4 | 23.2 | 23.9 | 26.6 | 31.0 | 10s | 20.0 | 14% | 14% | 9/10 | 7% / 6% |
| demand_shift_traffic | 26.8 | 22.4 | 22.9 | 23.3 | 26.3 | 30.6 | 8s | 20.6 | 10% | 8% | 9/10 | 7% / 6% |
| burst_traffic | 37.0 | 29.6 | 26.6 | 27.0 | 28.3 | 32.0 | 10s | 24.1 | 9% | 9% | 9/10 | 9% / 8% |
| alternating_heavy_traffic | 39.1 | 31.5 | 27.7 | 27.5 | 29.7 | 33.3 | 12s | 24.4 | 12% | 11% | 9/10 | 8% / 8% |
| asymmetric_peak_traffic | 71.5 | 75.2 | 77.3 | 78.2 | 79.6 | 82.4 | 6s | 51.7 | 33% | 28% | 10/10 | 54% / 28% |
| turning_conflict_traffic | 73.4 | 71.5 | 68.0 | 66.6 | 65.4 | 64.6 | 20s | 30.4 | 55% | 53% | 10/10 | 28% / 12% |
| emergency_balanced_traffic | 24.0 | 21.9 | 21.7 | 22.8 | 25.2 | 30.3 | 10s | 20.5 | 5% | 5% | 7/10 | 6% / 6% |
| emergency_right_heavy_traffic | 52.7 | 53.6 | 54.2 | 54.4 | 55.9 | 58.6 | 6s | 21.2 | 61% | 60% | 10/10 | 33% / 8% |
| emergency_peak_traffic | 66.5 | 54.9 | 48.7 | 43.3 | 41.7 | 42.9 | 15s | 44.7 | 8% | -7% | 1/10 | 15% / 16% |
| emergency_sparse_traffic | 13.3 | 14.8 | 17.6 | 19.0 | 23.3 | 28.3 | 6s | 4.0 | 77% | 70% | 10/10 | 5% / 2% |
| emergency_low_frequency_mixed_traffic | 19.6 | 18.1 | 20.2 | 21.7 | 23.9 | 28.9 | 8s | 15.1 | 25% | 17% | 9/10 | 6% / 5% |
| mixed_master_scenario | 86.1 | 67.4 | 61.6 | 55.8 | 54.2 | 52.6 | 20s | 22.7 | 63% | 57% | 3/3 | 3% / 2% |

Reading the table:

- The gain comes from unbalanced traffic. In single-direction, extreme-directional, direction-heavy, turning-conflict and sparse scenarios the gain is 53-100% and holds in every run. Fixed time keeps giving green to approaches with no vehicles. In the asymmetric peak scenario, where demand piles onto one approach, the gain is 28%.
- With balanced traffic the difference is small: 5-17% over a well-tuned fixed time, and fixed time wins some runs.
- In `peak_traffic` and `emergency_peak_traffic` demand is above capacity and roughly one vehicle in six is still queued when the run ends. Here the longest fixed greens (15-20 s) are on par with adaptive control or ahead. When capacity is not enough, reordering the greens does not help, while long greens lose less time to yellow.
- The 100% in `single_direction_traffic` is an edge case: the only active approach stays green.

## Camera adaptive

The camera controller uses the same decision rule and the same field of view as the ground-truth controller. The only differences are that vehicle counts come from YOLO11n detections and that the observation is taken once per second.

- Gain over the best fixed time: median 22%, mean 36%, lowest -8%.
- Ahead of fixed time on average in 21 of 22 scenarios.
- Camera minus ground truth: median -0.2 s, highest +1.1 s.

| Scenario | best fixed | ground truth | camera | camera gain (best fixed) | camera minus ground truth | camera ahead (runs) | not crossed: ground truth / camera |
|---|---:|---:|---:|---:|---:|---:|---:|
| balanced_traffic | 21.4 (8s) | 19.9 | 19.4 | 10% | -0.6 s | 7/10 | 6% / 6% |
| right_heavy_traffic | 51.9 (12s) | 21.5 | 21.1 | 59% | -0.5 s | 10/10 | 8% / 8% |
| vertical_heavy_traffic | 40.0 (15s) | 18.2 | 18.0 | 55% | -0.1 s | 10/10 | 5% / 5% |
| peak_traffic | 42.6 (20s) | 42.6 | 42.3 | 1% | -0.3 s | 5/10 | 16% / 16% |
| low_traffic | 14.6 (6s) | 12.5 | 12.4 | 15% | -0.1 s | 10/10 | 4% / 4% |
| turn_heavy_traffic | 23.4 (8s) | 20.8 | 20.2 | 14% | -0.7 s | 9/10 | 6% / 6% |
| single_direction_traffic | 39.3 (6s) | 0.0 | 0.0 | 100% | +0.0 s | 10/10 | 1% / 1% |
| extreme_directional_traffic | 55.8 (6s) | 17.5 | 16.8 | 70% | -0.7 s | 10/10 | 10% / 9% |
| sparse_traffic | 13.9 (6s) | 4.0 | 4.2 | 70% | +0.2 s | 10/10 | 2% / 2% |
| idle_intersection | 12.3 (6s) | 3.6 | 3.6 | 71% | +0.0 s | 10/10 | 3% / 3% |
| direction_shift_traffic | 23.2 (10s) | 20.0 | 19.4 | 16% | -0.6 s | 10/10 | 6% / 6% |
| demand_shift_traffic | 22.4 (8s) | 20.6 | 20.3 | 9% | -0.3 s | 7/10 | 6% / 6% |
| burst_traffic | 26.6 (10s) | 24.1 | 24.3 | 9% | +0.2 s | 9/10 | 8% / 8% |
| alternating_heavy_traffic | 27.5 (12s) | 24.4 | 24.4 | 11% | +0.1 s | 9/10 | 8% / 7% |
| asymmetric_peak_traffic | 71.5 (6s) | 51.7 | 51.1 | 28% | -0.6 s | 10/10 | 28% / 27% |
| turning_conflict_traffic | 64.6 (20s) | 30.4 | 29.4 | 55% | -1.0 s | 10/10 | 12% / 11% |
| emergency_balanced_traffic | 21.7 (10s) | 20.5 | 20.2 | 7% | -0.3 s | 8/10 | 6% / 6% |
| emergency_right_heavy_traffic | 52.7 (6s) | 21.2 | 20.3 | 62% | -1.0 s | 10/10 | 8% / 7% |
| emergency_peak_traffic | 41.7 (15s) | 44.7 | 45.2 | -8% | +0.4 s | 1/10 | 16% / 16% |
| emergency_sparse_traffic | 13.3 (6s) | 4.0 | 4.0 | 70% | +0.0 s | 10/10 | 2% / 2% |
| emergency_low_frequency_mixed_traffic | 18.1 (8s) | 15.1 | 15.2 | 16% | +0.1 s | 10/10 | 5% / 4% |
| mixed_master_scenario | 52.6 (20s) | 22.7 | 23.7 | 55% | +1.1 s | 3/3 | 2% / 2% |

The difference between the two adaptive controllers stays under a second per scenario and goes both ways. Since the model is close to perfect on simulation frames, this is expected: detection errors do not change the decisions. It says nothing about real camera footage (see the limitations below).

## Emergency vehicles

Average wait of emergency vehicles (s, vehicles that crossed):

| Scenario | best fixed | ground truth | camera |
|---|---:|---:|---:|
| emergency_balanced_traffic | 18.9 | 1.6 | 1.4 |
| emergency_right_heavy_traffic | 63.6 | 15.1 | 12.3 |
| emergency_peak_traffic | 50.1 | 23.0 | 19.9 |
| emergency_sparse_traffic | 17.9 | 0.3 | 0.8 |
| emergency_low_frequency_mixed_traffic | 18.0 | 1.0 | 1.4 |
| mixed_master_scenario | 54.6 | 7.4 | 8.6 |

This is where adaptive control is most clearly ahead. Waits are higher in `emergency_right_heavy_traffic` and `emergency_peak_traffic`. In these scenarios the queue can spill out of the frame; an emergency vehicle stuck at the back is only seen once it enters the frame, and priority starts from that point.

## What the simulation covers

- Repeatable comparison under identical traffic. With scenario, controller and seed fixed the result is identical (`tools/verify_determinism.py`).
- Demand levels defined relative to capacity: sparse traffic at v/c 0.20, balanced at 0.55-0.65, peak at 0.90 (see `docs/scenario_capacity_calibration.md`).
- Direction-heavy scenarios, demand that changes during the run, turning conflicts and emergency vehicles.
- Vehicles that accelerate, brake and follow the vehicle ahead; queues discharge one by one (`tools/verify_vehicle_motion.py`).
- Vehicle class detection from the image and signal decisions based on those detections.

## What the simulation simplifies

1. The images are synthetic. Frames are the simulation's own rendering: vehicles always have the same scale and look, and there is no lighting, weather, shadow, occlusion or camera angle. On real footage detection errors will affect control much more than they do here. Measuring that cost on real footage is the next step for the project.
2. The field of view is limited. The controller only sees the 900x900 frame. A queue that spills out of the frame cannot be counted; the rule adds 3 s of green when a queue reaches the edge as a rough correction. Emergency vehicles outside the frame are not seen.
3. Capacity is higher than in the recordings. The simulation discharges 1.00 veh/s per approach, the recordings from three real intersections show 0.45 veh/s. Since scenarios are defined relative to capacity the controller comparison holds, but waits in seconds do not carry over directly to a real intersection.
4. Demand is synthetic. Arrival intervals and direction weights are design choices and were not compared with count data from a real intersection.
5. One intersection. Vehicles leave on the exit road after crossing; spillback from a neighbouring intersection and green waves are not modeled.
6. No pedestrian phase. A 5 s minimum green is optimistic for a real urban intersection.
7. Only one approach is green at a time. There is no phase plan where opposite approaches go together, and no protected left turn.
8. All drivers behave the same: same acceleration, braking and following distance. Everyone always makes way for emergency vehicles.
