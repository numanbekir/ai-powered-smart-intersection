"""Checks the signal decisions against what happened afterwards.

A decision has two parts, the approach that gets the green and the length
of the green. Neither can be proven optimal, but both leave a trace:

- Too short: fewer vehicles crossed than were on the approach when the
  green was given. The rest have to wait a full cycle.
- Too long: the green kept running after the last vehicle had crossed,
  while other approaches were waiting.
- Direction: how often the chosen approach was the one with the most
  vehicles, or the one that had been red the longest.

Only greens given while another approach had vehicles are counted. The
fixed-time controller is run on the same scenarios for comparison.

Run directly: python tools/verify_decisions.py
"""

import copy
import os
import sys
from multiprocessing import Pool
from pathlib import Path
from statistics import mean

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.controller_version_registry import ControllerVersionRegistry
from core.scenario_registry import ScenarioRegistry
from simulation.engine import SimulationEngine
from state_providers.ground_truth_provider import GroundTruthStateProvider

SCENARIOS = [
    "low_traffic",
    "balanced_traffic",
    "right_heavy_traffic",
    "peak_traffic",
    "emergency_balanced_traffic",
]
SIMULATION_TIME = 480.0
# A green that runs this long after its last crossing counts as idle.
IDLE_LIMIT = 3.0
DIRECTIONS = ["right", "down", "left", "up"]


class DecisionCheck:
    def __init__(self, engine):
        self.engine = engine
        self.truth = GroundTruthStateProvider(engine)
        self.phases = []
        self.current = None
        self.previous_key = None
        self.last_green_end = {direction: 0.0 for direction in DIRECTIONS}

    def __call__(self, engine):
        controller = engine.controller
        direction = engine.directionNumbers[controller.currentGreen]
        yellow = controller.currentYellow == 1
        now = engine.simulation_elapsed
        crossed = engine.vehicles[direction]["crossed"]

        key = (direction, yellow)
        started = self.previous_key is None or (
            not yellow and (self.previous_key[0] != direction or self.previous_key[1])
        )
        self.previous_key = key

        if started:
            self.close(now)
            counts = self.truth.get_state()
            others = [d for d in DIRECTIONS if d != direction and counts[d] > 0]
            red_times = {d: now - self.last_green_end[d] for d in DIRECTIONS}
            self.current = {
                "direction": direction,
                "start": now,
                "counted": counts[direction],
                "contested": bool(others),
                "most_vehicles": counts[direction] == max(counts.values()),
                "longest_red": bool(others)
                and red_times[direction] >= max(red_times[d] for d in others),
                "crossed_at_start": crossed,
                "last_crossing": now,
                "last_count": crossed,
                "green_end": None,
            }
            return

        phase = self.current
        if phase is None:
            return
        if crossed > phase["last_count"]:
            phase["last_count"] = crossed
            if not yellow:
                phase["last_crossing"] = now
        if yellow and phase["green_end"] is None:
            phase["green_end"] = now
            self.last_green_end[direction] = now

    def close(self, now):
        phase = self.current
        if phase is None or phase["green_end"] is None:
            return
        phase["green"] = phase["green_end"] - phase["start"]
        phase["crossed"] = phase["last_count"] - phase["crossed_at_start"]
        phase["left_behind"] = max(0, phase["counted"] - phase["crossed"])
        phase["idle_tail"] = phase["green_end"] - phase["last_crossing"]
        self.phases.append(phase)


def run(case):
    scenario_id, mode = case
    scenario = copy.deepcopy(ScenarioRegistry().get_by_id(scenario_id))
    config = scenario["config"]
    config["random_seed"] = 42
    config["playback_speed"] = 8.0
    config["simulation_time"] = SIMULATION_TIME

    engine = SimulationEngine(
        scenario=scenario,
        test_name="decision_check",
        controller_mode=mode,
        controller_version=(
            ControllerVersionRegistry().get("adaptive_ground_truth") if mode == "adaptive" else None
        ),
        state_provider_id="ground_truth_v1",
        headless=True,
    )
    check = DecisionCheck(engine)
    engine.tick_listeners.append(check)
    engine.run()

    phases = [phase for phase in check.phases if phase["contested"]]
    if not phases:
        return f"{scenario_id:<28} {mode:<9} no contested green"

    def share(condition):
        return 100.0 * sum(1 for phase in phases if condition(phase)) / len(phases)

    return (
        f"{scenario_id:<28} {mode:<9} greens {len(phases):>3}  "
        f"mean green {mean(p['green'] for p in phases):4.1f}s  "
        f"too short {share(lambda p: p['left_behind'] > 0):3.0f}% "
        f"(left behind {mean(p['left_behind'] for p in phases):3.1f})  "
        f"idle end {share(lambda p: p['idle_tail'] > IDLE_LIMIT):3.0f}% "
        f"(idle {mean(p['idle_tail'] for p in phases):3.1f}s)  "
        f"most vehicles {share(lambda p: p['most_vehicles']):3.0f}%  "
        f"longest red {share(lambda p: p['longest_red']):3.0f}%"
    )


def main():
    cases = [(scenario_id, mode) for scenario_id in SCENARIOS for mode in ("fixed", "adaptive")]
    with Pool(min(len(cases), max(1, (os.cpu_count() or 2) - 2))) as pool:
        for line in pool.map(run, cases):
            print(line)


if __name__ == "__main__":
    main()
