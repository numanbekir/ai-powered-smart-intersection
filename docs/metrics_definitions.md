# Metric Definitions

These are the metrics written to every run result. They are computed in `collect_results()` in `simulation/engine.py` and `summarize_direction()` in `simulation/metrics.py`.

No single metric is enough. A low average wait can hide a few vehicles that waited a very long time, so results are read across several groups of metrics.

## 1. Wait metrics

A vehicle's wait time (`waitTime`) accumulates in simulated seconds on every tick while it is held by the signal (`Vehicle.update_signal_wait_time`). It does not depend on playback speed.

| Metric | Definition |
|---|---|
| `overall_avg_wait` | Average wait of all vehicles that crossed |
| `overall_median_wait` (`overall_wait_p50`) | Median wait, less sensitive to outliers |
| `overall_max_wait` | Longest wait of a single vehicle. A high value points to an approach being neglected |
| `overall_wait_p90` / `p95` / `p99` | Wait of the 10%, 5% and 1% of vehicles that waited the longest |

Scope: these metrics only cover vehicles that crossed. Vehicles still queued when the run ends are not part of the average. When demand exceeds capacity this makes `overall_avg_wait` look better than it is, so it should be read together with the metrics below.

### Warmup, delay and vehicles that did not cross

| Metric / setting | Definition |
|---|---|
| `warmup_time` (setting) | Vehicles spawned before this time are left out of every statistic, and queue sampling starts after it. Default 0. Used because the first minutes of a run that starts from an empty intersection are not representative |
| `overall_avg_delay` / `overall_delay_p95` | Control delay: time the vehicle crossed the stop line, minus the time it spawned, minus the time it would have needed at free-flow speed. Includes slow progress in a queue, not only standing at red |
| `vehicles_measured` | Vehicles spawned after the warmup, i.e. included in the measurement |
| `vehicles_uncrossed` | Of those, the ones that had not crossed when the run ended |
| `uncrossed_avg_wait` | Average wait of the uncrossed vehicles up to the end of the run |

`tools/baseline_sweep_report.py` combines the two groups and reports the average wait of every measured vehicle: `(overall_avg_wait × crossed + uncrossed_avg_wait × uncrossed) / vehicles_measured`. Because the wait of uncrossed vehicles is cut off at the end of the run, this is still a lower bound in saturated scenarios.

## 2. Queue metrics

| Metric | Definition |
|---|---|
| `queue_length_average` | Average queue length, sampled every tick |
| `queue_length_peak` | Highest queue length observed |

What is counted: queue length is the number of all vehicles on the approach that have not crossed yet. It includes vehicles still driving towards the intersection, so it is "vehicles on the approach" rather than a strict standing queue.

Sampling: the queue is sampled once per tick, unweighted. At higher playback speed a tick covers more time and short spikes can be missed. All sweep runs use the same playback speed, so they are comparable with each other. Absolute values from different playback speeds are not.

## 3. Throughput

| Metric | Definition |
|---|---|
| `total_crossed` | Vehicles that crossed during the run |
| `normal_vehicle_crossed` / `emergency_crossed` | The same number split into regular and emergency vehicles |

## 4. Emergency vehicle metrics

| Metric | Definition |
|---|---|
| `emergency_spawned` | Emergency vehicles spawned |
| `emergency_crossed` | Emergency vehicles that crossed |
| `emergency_avg_wait` / `emergency_max_wait` | Average and longest wait of emergency vehicles |
| `emergency_wait_p95` / `p99` | Wait of the 5% and 1% of emergency vehicles that waited the longest |
| `emergency_hold_count` / `emergency_total_hold_time` / `emergency_hold_max_time` | How many times, for how long in total and for how long at most a running green was extended to let an emergency vehicle through |
| `emergency_hold_success_count` | How many of the vehicles that got an extension actually crossed |
| `priority_activation_count` | Number of greens given, or cut, because of emergency priority |

The "crossed only" scope of the wait metrics applies here too. With fixed-time control the hold and priority counts stay at 0, since emergency vehicles get no special treatment.

## 5. Per-direction metrics

For each approach (`right`, `down`, `left`, `up`) the result also has `avg_wait`, `median_wait`, `max_wait`, `crossed`, `queue_length_average`, `queue_length_peak` and `wait_p90` / `p95` / `p99`. This is where you can see whether a controller keeps neglecting one approach.
