# Simulation Engine (`simulation/engine.py`, `simulation/vehicle.py`)

`SimulationEngine` handles spawning, vehicle motion, signal phases, metric collection and drawing. Windowed and headless runs use the same code.

## Runtime: two threads, one clock

Two threads run next to the main loop:

- Controller (`controller.run`): picks and runs the signal phases.
- Spawner (`generateVehicles`): creates vehicles with a random approach, type and turn.

Time is not wall-clock time but a single counter, `simulation_elapsed`. Each tick advances it by `playback speed / fps`. `scaled_sleep()` does not sleep in real time, it waits for the counter to reach the target. Whatever the playback speed, the same scenario and seed give the same result.

The main loop does not move on to the next tick until both threads have finished their work for the current one and are waiting again (`wait_for_workers()`). This keeps results stable under CPU load as well.

## Determinism

With scenario, controller, state provider and seed fixed, the result is identical. `tools/verify_determinism.py` checks this with two back-to-back runs and again under artificial CPU load. It should be run after any change to the engine, the controllers or the decision rule.

## Motion model

Vehicles accelerate, brake and follow the vehicle ahead. Values are in pixels and simulated seconds:

| Value | Meaning |
|---|---|
| `acceleration` = 25 | acceleration |
| `comfortBraking` = 40 | normal braking |
| `hardBraking` = 90 | hard braking, used for the stop/go decision when the light changes |
| `timeHeadway` = 0.7 | time gap kept to the vehicle ahead |
| `startGap` = 5 | gap that must open ahead of a standing vehicle before it moves off |
| `stoppingGap` = 25 | distance between standing vehicles |
| `turnSpeedFactor` = 0.7 | speed ratio while turning |

Rules:

- Following: speed never exceeds what the gap ahead allows. Behind a standing vehicle the slowdown follows a braking curve instead of a long creep.
- Starting: a standing vehicle does not move until a `startGap` has opened ahead of it, so a queue discharges one vehicle after another rather than as a block.
- Stop line: a vehicle stops at the line unless the light is green. A vehicle too close to stop when the light changes goes through.
- Inside the intersection: even on green, a vehicle waits at the line while a vehicle from another approach is still inside.
- Turning: a turning vehicle follows a fixed path at lower speed and then follows the traffic on its exit road.

Measured saturation capacity is 1.00 veh/s per approach (two lanes, one vehicle every 2 s per lane), measured with `tools/measure_current_capacity.py`. `tools/verify_vehicle_motion.py` checks four rules: speed changes without jumps, a vehicle starts within 1.5 s after the one ahead pulls away, a vehicle with a free road ahead never stands still, and standing vehicles never overlap.

For how this capacity compares with real intersections, see `docs/scenario_capacity_calibration.md`.

## Spawn point

A vehicle appears at the fixed spawn point of its lane, or behind the last vehicle of that lane if it has not moved away from the spawn point yet (`Vehicle.place_at_spawn()`).

## The simulation window runs in its own process

The UI uses Tkinter, the simulation window uses pygame. Running both in one process made the app crash when a UI window was opened after a simulation. The simulation therefore runs in a separate process (`simulation/runner.py`) and sends its result back through a pipe. The UI language is passed to that process as well.

## Side panel

`simulation/panel.py` draws the panel on the right: a table of the approaches (signal, vehicle count, wait, crossed), the last decision, run totals and the recent greens. With the camera controller the table shows the camera's count, and when it differs from the exact count the actual number is shown under it.

## Metric collection

Wait time accumulates in simulated seconds on every tick while a vehicle is held by the signal, independent of playback speed. Definitions are in `docs/metrics_definitions.md`.

## Known limitations

- Only one intersection is modeled. Corridor or network coordination cannot be tested.
- There is no pedestrian phase. A 5 s minimum green is optimistic for a real urban intersection.
- Only one approach is green at a time. Phase plans where two opposite approaches go together are not modeled.
- The overlap check does not cover vehicles in the middle of a turn.
- Vehicles that have crossed are not removed from memory, so memory use grows on very long runs.
- Queue length is sampled once per tick, unweighted. Absolute values taken at different playback speeds are not comparable.
