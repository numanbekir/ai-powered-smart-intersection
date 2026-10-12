"""Measures the CURRENT engine's per-direction saturated discharge capacity
(single direction, continuous green, unlimited demand) so it can be compared
directly, in the same unit, against real-world recordings
(data/real_world_calibration.csv, see tools/real_world_calibration_analysis.py).

The previous such measurement (~1.116 veh/s, see docs/scenario_capacity_calibration.md)
was produced by a script that no longer exists in this project and whose exact
scope (single direction vs. whole-intersection) is not fully recoverable from
the doc alone -- this re-measures cleanly against the current code instead of
guessing at the old one.

Method: fixed-time controller, one direction's green_time set far longer than
simulation_time (so it never leaves green), all demand routed to that
direction, spawn_interval short enough to guarantee a standing queue the
whole run. crossed / simulation_time = saturated per-direction capacity.

Run directly: python tools/measure_current_capacity.py
"""

import copy
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.scenario_registry import ScenarioRegistry
from simulation.engine import SimulationEngine

SIMULATION_TIME = 300
SEEDS = [42, 101, 202]
TARGET_DIRECTION = "right"


def build_saturated_scenario(base_scenario):
    scenario = copy.deepcopy(base_scenario)
    cfg = scenario["config"]
    cfg["simulation_time"] = SIMULATION_TIME
    cfg["playback_speed"] = 8.0
    cfg["spawn_interval"] = 0.2
    cfg["direction_density"] = {
        d: (100 if d == TARGET_DIRECTION else 0)
        for d in ["right", "down", "left", "up"]
    }
    cfg["fixed"]["initial_green"] = TARGET_DIRECTION
    cfg["fixed"]["green_time"] = SIMULATION_TIME * 10
    cfg["emergency"]["enabled"] = False
    return scenario


def run_once(scenario, seed):
    scenario = copy.deepcopy(scenario)
    scenario["config"]["random_seed"] = seed

    engine = SimulationEngine(
        scenario=scenario,
        test_name="capacity_measurement",
        controller_mode="fixed",
        state_provider_id="ground_truth_v1",
        headless=True,
    )
    outcome = engine.run()
    return outcome["result"]


def main():
    scenario_registry = ScenarioRegistry()
    base_scenario = scenario_registry.get_by_id("balanced_traffic")
    scenario = build_saturated_scenario(base_scenario)

    print("=" * 70)
    print(f"GUNCEL SIM KAPASITE OLCUMU: yon={TARGET_DIRECTION}, "
          f"simulation_time={SIMULATION_TIME}s, spawn_interval=0.2")
    print("=" * 70)

    rates = []
    for seed in SEEDS:
        result = run_once(scenario, seed)
        crossed = result["per_direction"][TARGET_DIRECTION]["crossed"]
        rate = crossed / SIMULATION_TIME
        rates.append(rate)
        print(f"  seed={seed:<5} crossed={crossed:<6} rate={rate:.3f} veh/s")

    avg = sum(rates) / len(rates)
    print(f"\nOrtalama: {avg:.3f} veh/s (yon basi, 2 seritli)")
    print(f"Gercek veri (tools/real_world_calibration_analysis.py) ile karsilastirin.")


if __name__ == "__main__":
    main()
