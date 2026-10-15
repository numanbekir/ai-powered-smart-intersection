# Scenario Demand and Capacity

Scenario demand is defined relative to the measured capacity (v/c). This document covers how capacity was measured, which ratio each scenario is set to, and how the simulation compares with real intersection recordings.

## Measured capacity

`tools/measure_current_capacity.py` keeps one approach on permanent green, feeds it continuous demand and divides the number of vehicles that cross by the elapsed time.

Result: 1.00 veh/s per approach. There are two lanes, each discharging one vehicle every 2 seconds.

## How demand is generated

The spawner creates one vehicle every `spawn_interval` simulated seconds. Its approach is picked with the `direction_density` weights. These weights set how demand is split across approaches, not the total.

```
v/c = (1 / spawn_interval) / capacity
```

This ratio ignores the time lost to yellow, so actual utilization is a bit higher.

## Scenario ratios

| `spawn_interval` | v/c | Scenarios |
|---:|---:|---|
| 6.66 | 0.15 | `idle_intersection` |
| 4.99 | 0.20 | `sparse_traffic`, `emergency_sparse_traffic` |
| 2.86 | 0.35 | `low_traffic` |
| 2.22 | 0.45 | `emergency_low_frequency_mixed_traffic` |
| 1.82 | 0.55 | `balanced_traffic`, `right_heavy_traffic`, `vertical_heavy_traffic`, `turn_heavy_traffic`, `extreme_directional_traffic`, `direction_shift_traffic`, `emergency_balanced_traffic`, `emergency_right_heavy_traffic` |
| 1.54 | 0.65 | `single_direction_traffic`, `burst_traffic`, `alternating_heavy_traffic`, `turning_conflict_traffic` |
| 1.11 | 0.90 | `peak_traffic`, `asymmetric_peak_traffic`, `emergency_peak_traffic` |

`demand_shift_traffic` and `mixed_master_scenario` change demand during the run (`dynamic_spawn_interval_schedule`). `mixed_master_scenario` is a 30-minute run that plays the other scenarios back to back in 90-second blocks.

In scenarios that pile demand onto one approach (`right_heavy`, `extreme_directional`, `asymmetric_peak`) that approach's own ratio is higher than the table value and it can saturate on its own.

## Comparison with real intersections

Three intersections were recorded for 5-10 minutes each. For every green phase the start of green, the first vehicle crossing, the end of green and the number of vehicles that crossed were marked by hand (`data/real_world_calibration.csv`, 22 phases). Summarized with `tools/real_world_calibration_analysis.py`:

| | Recordings | Simulation |
|---|---:|---:|
| Discharge rate (per approach, 2 lanes) | 0.45 veh/s on average | 1.00 veh/s |
| Time from green to first vehicle crossing | 2.95 s on average | about 2 s |

The simulation discharges roughly twice as fast as the recordings. An earlier version matched the recorded capacity by increasing the gap between vehicles, but vehicles then drove with unrealistic gaps on screen. When the motion model was rewritten, acceleration, braking and following were tuned to look right, and capacity came out at 1.00 veh/s.

The scenario v/c ratios were kept: every `spawn_interval` was multiplied by the ratio of old to new capacity (0.4775). As a result:

- Comparing controllers with each other is valid, since they all run at the same capacity and the same utilization.
- Absolute waits in seconds and hourly vehicle counts do not carry over directly to a real intersection.

The recordings are short single-approach videos, and in some of them the queue cleared before the green ended. So 0.45 veh/s is closer to a lower bound of the saturation capacity.
