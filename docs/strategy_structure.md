# Decision Rule (`controllers/strategies/demand_strategy.py`)

Adaptive control has a single decision rule, `DemandStrategy`. The rule does not read the simulation itself. It only receives an observation of the four approaches, and the same code runs with two different observation sources:

| Controller | Observation source |
|---|---|
| `adaptive_ground_truth` (Adaptive - Ground Truth) | `GroundTruthStateProvider`: exact count of the vehicles inside the camera frame |
| `adaptive_camera` (Adaptive - Camera) | `YoloStateProvider`: YOLO11n detections on the same frame, once per simulated second |

Both sources cover the same field of view. The difference between them comes from detection errors and the one-second observation interval, and that difference is what the camera costs in control quality.

## Observation

For each approach:

- `visible_count`: vehicles visible in the frame that have not reached the stop line yet. A vehicle counts once at least 30% of it is inside the frame.
- `is_saturated`: true when a vehicle is within 70 px of the frame edge. The queue most likely continues outside the frame, so the count is a lower bound.
- `emergency`: type of the nearest emergency vehicle, its distance to the stop line, whether it is standing and how many vehicles are ahead of it. `None` if there is none.

## Choosing the approach

```
index = vehicles + λ · max(0, red time − soft limit)
```

The approach with the highest index gets the green. On top of that there is a cycle-fairness rule: no approach gets a second green until every approach with vehicles has had one. Defaults are λ = 1.5 and a 20 s soft limit.

In practice, when more than one approach has vehicles, the chosen approach is the one that has been red the longest in 97-100% of greens. So under load the order is effectively round-robin. Where the rule differs from fixed time is that it skips empty approaches and sizes each green to the number of vehicles.

## Green time

```
green = start-up time + vehicles / discharge rate   (+ saturation bonus)
```

The result is clamped between the minimum and maximum green. Defaults: 2 s start-up time, 1 veh/s discharge rate, 3 s saturation bonus, 5 s minimum green, 30 s maximum green, 3 s yellow. The saturation bonus is only added when `is_saturated` is true.

When a green runs out and no other approach has vehicles, it simply continues without going through yellow.

## Emergency vehicles

- Priority: the approach where an emergency vehicle is seen gets the next green. If there are several, the one closest to the stop line wins. The green lasts as long as the vehicle needs to arrive: distance / speed + 1 s per vehicle ahead + 2 s margin.
- Preemption: if an emergency vehicle shows up on another approach, the current green is cut once the minimum green has passed.
- Extension: if the emergency vehicle on the green approach will not make it in the remaining time, the green is extended, by at most 20 s in total.
- Starvation guard: no priority is given if another approach has been red for more than 90 s. This stops an emergency vehicle stuck in a queue from holding up everyone else indefinitely.

## Controller vs. rule

`controllers/adaptive_controller.py` handles the timing: green, yellow, one-second steps. It never overrides the rule. With every green the rule also returns a short explanation, which is the "Last decision" text on the side panel.

The parameters live in `ADAPTIVE_PARAMS` in `core/config_defaults.py` and are written from there to `data/controller_versions.json`.

## Auditing the decisions

`tools/verify_decisions.py` compares every green with what happened afterwards: how many vehicles crossed in the time given, whether the green kept running after the last vehicle, and whether the chosen approach was the busiest or the longest-waiting one. The same scenarios are also run with fixed-time control.

Latest run (one run per scenario, only greens given while another approach had vehicles):

| Scenario | Idle green: fixed | Idle green: adaptive | Too-short green: adaptive |
|---|---:|---:|---:|
| `low_traffic` | 42% | 25% | 2% |
| `balanced_traffic` | 24% | 17% | 0% |
| `right_heavy_traffic` | 27% | 24% | 3% |
| `peak_traffic` | 0% | 4% | 0% |
| `emergency_balanced_traffic` | 24% | 32% | 0% |

At low and medium demand the adaptive rule wastes less green time. In saturated traffic every approach has a queue, so neither controller leaves a green idle. In the emergency scenario the adaptive rule is worse. The likely reason is that a priority green or an extension is sized to the emergency vehicle's arrival, not to the queue.

## Known limitations

- The observation is limited to what is in the frame. A queue that spills out of the frame cannot be counted; the saturation bonus is a rough correction.
- An emergency vehicle waiting outside the frame is not seen. Priority starts when it enters the frame.
- The discharge rate is not measured, it is a fixed assumption.
- The parameters were picked with a single comparison, there is no per-scenario tuning.
