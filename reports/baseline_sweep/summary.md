# Fixed-time sweep and adaptive comparison

Average wait (s), mean over runs. Covers every measured vehicle: the wait of those that crossed and, for those still queued when the run ended, the wait up to that moment. Gain is the reduction in wait.

- Scenarios: 22
- Gain over the default fixed time (10s): mean 40%, lowest 5%
- Gain over each scenario's best fixed time: median 22%, mean 35%, lowest -7%
- Scenarios where adaptive is ahead on average: 20/22
- Scenarios where adaptive is ahead in at least 80% of runs: 18/22
- If a single fixed time had to be picked (mean ratio to the default per scenario, lower is better): 6s=1.066, 8s=0.986, 10s=1.000, 12s=1.028, 15s=1.120, 20s=1.265

| Scenario | fixed 6s | fixed 8s | fixed 10s | fixed 12s | fixed 15s | fixed 20s | best fixed | best adaptive | gain (fixed 10s) | gain (best fixed) | adaptive ahead (runs) | not crossed: fixed / adaptive |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| balanced_traffic | 25.2 | 21.4 | 22.4 | 23.4 | 25.9 | 30.6 | 8s | 19.9 (ground truth) | 11% | 7% | 6/10 | 7% / 6% |
| right_heavy_traffic | 52.6 | 52.6 | 53.8 | 51.9 | 55.9 | 56.9 | 12s | 21.5 (ground truth) | 60% | 59% | 10/10 | 24% / 8% |
| vertical_heavy_traffic | 54.6 | 46.6 | 42.4 | 41.6 | 40.0 | 42.1 | 15s | 18.2 (ground truth) | 57% | 55% | 10/10 | 15% / 5% |
| peak_traffic | 66.4 | 54.8 | 48.9 | 44.4 | 43.0 | 42.6 | 20s | 42.6 (ground truth) | 13% | -0% | 5/10 | 14% / 16% |
| low_traffic | 14.6 | 15.9 | 17.7 | 20.6 | 23.6 | 28.6 | 6s | 12.5 (ground truth) | 29% | 15% | 10/10 | 4% / 4% |
| turn_heavy_traffic | 27.6 | 23.4 | 23.5 | 24.3 | 26.6 | 30.9 | 8s | 20.8 (ground truth) | 11% | 11% | 8/10 | 7% / 6% |
| single_direction_traffic | 39.3 | 52.3 | 64.3 | 72.8 | 87.6 | 108.7 | 6s | 0.0 (ground truth) | 100% | 100% | 10/10 | 91% / 1% |
| extreme_directional_traffic | 55.8 | 67.7 | 77.1 | 82.6 | 91.4 | 101.4 | 6s | 17.5 (ground truth) | 77% | 69% | 10/10 | 67% / 10% |
| sparse_traffic | 13.9 | 15.3 | 16.8 | 19.2 | 22.4 | 28.3 | 6s | 4.0 (ground truth) | 76% | 71% | 10/10 | 5% / 2% |
| idle_intersection | 12.3 | 13.4 | 16.6 | 18.3 | 23.4 | 25.9 | 6s | 3.6 (ground truth) | 79% | 71% | 10/10 | 4% / 3% |
| direction_shift_traffic | 28.7 | 23.4 | 23.2 | 23.9 | 26.6 | 31.0 | 10s | 20.0 (ground truth) | 14% | 14% | 9/10 | 7% / 6% |
| demand_shift_traffic | 26.8 | 22.4 | 22.9 | 23.3 | 26.3 | 30.6 | 8s | 20.6 (ground truth) | 10% | 8% | 9/10 | 7% / 6% |
| burst_traffic | 37.0 | 29.6 | 26.6 | 27.0 | 28.3 | 32.0 | 10s | 24.1 (ground truth) | 9% | 9% | 9/10 | 9% / 8% |
| alternating_heavy_traffic | 39.1 | 31.5 | 27.7 | 27.5 | 29.7 | 33.3 | 12s | 24.4 (ground truth) | 12% | 11% | 9/10 | 8% / 8% |
| asymmetric_peak_traffic | 71.5 | 75.2 | 77.3 | 78.2 | 79.6 | 82.4 | 6s | 51.7 (ground truth) | 33% | 28% | 10/10 | 54% / 28% |
| turning_conflict_traffic | 73.4 | 71.5 | 68.0 | 66.6 | 65.4 | 64.6 | 20s | 30.4 (ground truth) | 55% | 53% | 10/10 | 28% / 12% |
| emergency_balanced_traffic | 24.0 | 21.9 | 21.7 | 22.8 | 25.2 | 30.3 | 10s | 20.5 (ground truth) | 5% | 5% | 7/10 | 6% / 6% |
| emergency_right_heavy_traffic | 52.7 | 53.6 | 54.2 | 54.4 | 55.9 | 58.6 | 6s | 21.2 (ground truth) | 61% | 60% | 10/10 | 33% / 8% |
| emergency_peak_traffic | 66.5 | 54.9 | 48.7 | 43.3 | 41.7 | 42.9 | 15s | 44.7 (ground truth) | 8% | -7% | 1/10 | 15% / 16% |
| emergency_sparse_traffic | 13.3 | 14.8 | 17.6 | 19.0 | 23.3 | 28.3 | 6s | 4.0 (ground truth) | 77% | 70% | 10/10 | 5% / 2% |
| emergency_low_frequency_mixed_traffic | 19.6 | 18.1 | 20.2 | 21.7 | 23.9 | 28.9 | 8s | 15.1 (ground truth) | 25% | 17% | 9/10 | 6% / 5% |
| mixed_master_scenario | 86.1 | 67.4 | 61.6 | 55.8 | 54.2 | 52.6 | 20s | 22.7 (ground truth) | 63% | 57% | 3/3 | 3% / 2% |
