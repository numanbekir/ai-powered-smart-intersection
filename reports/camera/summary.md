# Fixed time, ground-truth adaptive and camera adaptive

Average wait (s), every measured vehicle. All three controllers ran on the same scenarios and seeds.
The camera controller uses the same decision rule as the ground-truth controller; its only input is the YOLO detections.

- Camera gain over the best fixed time: median 22%, mean 36%, lowest -8%
- Scenarios where the camera controller beats fixed time on average: 21/22
- Camera minus ground truth: median -0.2 s, highest +1.1 s

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

## Average wait of emergency vehicles (s)

| Scenario | best fixed | ground truth | camera |
|---|---:|---:|---:|
| emergency_balanced_traffic | 18.9 | 1.6 | 1.4 |
| emergency_right_heavy_traffic | 63.6 | 15.1 | 12.3 |
| emergency_peak_traffic | 50.1 | 23.0 | 19.9 |
| emergency_sparse_traffic | 17.9 | 0.3 | 0.8 |
| emergency_low_frequency_mixed_traffic | 18.0 | 1.0 | 1.4 |
| mixed_master_scenario | 54.6 | 7.4 | 8.6 |
