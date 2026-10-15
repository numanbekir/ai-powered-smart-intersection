"""Checks the vehicle motion model against four observable rules.

1. Speed changes gradually: no jump larger than the acceleration and
   hard-braking limits allow (px/s^2).
2. When the vehicle ahead pulls away, the one behind starts within 1.5 s.
3. A vehicle with a free road ahead never stands still.
4. Standing vehicles close up to the standing gap and no two vehicles
   overlap inside the camera frame.

Run directly: python tools/verify_vehicle_motion.py
"""

import copy
import os
import sys
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pygame

from core.controller_version_registry import ControllerVersionRegistry
from core.scenario_registry import ScenarioRegistry
from simulation.engine import SimulationEngine

SCENARIOS = ["balanced_traffic", "peak_traffic", "turn_heavy_traffic", "emergency_balanced_traffic"]
SIMULATION_TIME = 240.0
REACTION_LIMIT = 1.5
FRAME = pygame.Rect(0, 0, 900, 900)


class MotionCheck:
    CRAWL_SPEED = 5.0

    def __init__(self, engine):
        self.engine = engine
        self.last_velocity = {}
        self.standing_since = {}
        self.leader_started = {}
        self.max_acceleration = 0.0
        self.max_braking = 0.0
        self.hard_stops = 0
        self.reactions = []
        self.free_road_stops = 0
        self.standing_gaps = []
        self.overlaps = 0
        self.samples = 0

    def rect(self, vehicle):
        rect = vehicle.image.get_rect()
        return pygame.Rect(int(vehicle.x), int(vehicle.y), rect.width, rect.height)

    def __call__(self, engine):
        dt = engine.current_simulation_delta
        now = engine.simulation_elapsed
        placed = [v for v in engine.simulation if v._placed]

        for vehicle in placed:
            key = id(vehicle)
            previous = self.last_velocity.get(key)
            if previous is not None and dt > 0:
                change = (vehicle.velocity - previous) / dt
                self.max_acceleration = max(self.max_acceleration, change)
                # Coming to rest from a crawl is a snap of a few px/s and
                # is not counted as braking.
                if previous >= self.CRAWL_SPEED:
                    self.max_braking = max(self.max_braking, -change)
                    if -change > engine.hardBraking * 1.05:
                        self.hard_stops += 1
            self.last_velocity[key] = vehicle.velocity

            if vehicle.crossed == 1 or vehicle.rotateAngle != 0:
                continue

            heading = vehicle.HEADING[vehicle.direction]
            leader = vehicle.leader_before_turn()
            standing = vehicle.velocity == 0

            if leader is not None and leader.rotateAngle == 0:
                gap = vehicle.gap_to(leader, heading)
                if standing and leader.velocity == 0:
                    self.standing_gaps.append(gap)

                # Reaction: both stood in a queue, the leader starts moving.
                if standing and leader.velocity > 0 and gap < engine.stoppingGap + 15:
                    self.leader_started.setdefault(key, now)
                elif not standing and key in self.leader_started:
                    self.reactions.append(now - self.leader_started.pop(key))
                elif leader.velocity == 0:
                    self.leader_started.pop(key, None)

            if standing:
                red = not vehicle.controller.is_green(vehicle.direction_number)
                at_line = vehicle.distance_ahead(heading, engine.defaultStop[vehicle.direction]) < 3
                blocked = leader is not None and vehicle.gap_to(leader, heading) < engine.stoppingGap + engine.startGap
                waiting_for_junction = at_line and vehicle.junction_blocked()
                if not blocked and not (red and at_line) and not waiting_for_junction:
                    since = self.standing_since.setdefault(key, now)
                    # One tick of standstill is the vehicle arriving at rest.
                    if now - since > 0.5:
                        self.free_road_stops += 1
                        self.standing_since[key] = float("inf")
                else:
                    self.standing_since.pop(key, None)
            else:
                self.standing_since.pop(key, None)

        self.samples += 1
        if self.samples % 15 == 0:
            visible = [(v, self.rect(v)) for v in placed if FRAME.colliderect(self.rect(v))]
            for i, (_a, rect_a) in enumerate(visible):
                for _b, rect_b in visible[i + 1:]:
                    # The bounding box of a vehicle in mid-turn is larger
                    # than the vehicle, so those pairs are not compared.
                    if 0 < _a.rotateAngle < 90 or 0 < _b.rotateAngle < 90:
                        continue
                    if rect_a.inflate(-4, -4).colliderect(rect_b.inflate(-4, -4)):
                        self.overlaps += 1


def run(scenario_id, controller_mode, version_id, playback_speed):
    scenario = copy.deepcopy(ScenarioRegistry().get_by_id(scenario_id))
    config = scenario["config"]
    config["random_seed"] = 42
    config["playback_speed"] = playback_speed
    config["simulation_time"] = SIMULATION_TIME

    engine = SimulationEngine(
        scenario=scenario,
        test_name="motion_check",
        controller_mode=controller_mode,
        controller_version=ControllerVersionRegistry().get(version_id) if version_id else None,
        state_provider_id="ground_truth_v1",
        headless=True,
    )
    check = MotionCheck(engine)
    engine.tick_listeners.append(check)
    engine.run()
    check.crossed = sum(engine.vehicles[d]["crossed"] for d in engine.directionNumbers.values())
    return check


# (scenario, controller mode, controller version, playback speed). The tick
# length depends on the playback speed, so the slowest and a fast one are
# both covered.
CASES = [
    (scenario_id, mode, version, 2.0)
    for scenario_id in SCENARIOS
    for mode, version in (("fixed", None), ("adaptive", "adaptive_ground_truth"))
] + [
    ("balanced_traffic", "fixed", None, 1.0),
    ("peak_traffic", "adaptive", "adaptive_ground_truth", 8.0),
]


def evaluate(case):
    scenario_id, mode, version, playback_speed = case
    check = run(scenario_id, mode, version, playback_speed)
    engine = check.engine
    gaps = check.standing_gaps
    reactions = check.reactions
    ok = (
        check.max_acceleration <= engine.acceleration * 1.05
        and check.hard_stops == 0
        and (not reactions or max(reactions) <= REACTION_LIMIT)
        and check.free_road_stops == 0
        and check.overlaps == 0
        and check.crossed > 0
        and (not gaps or (min(gaps) >= engine.stoppingGap - 1 and max(gaps) <= engine.stoppingGap + 6))
    )
    line = (
        f"{'OK  ' if ok else 'FAIL'} {scenario_id:<28} {mode:<8} x{playback_speed:<3} crossed {check.crossed:<4} "
        f"accel max {check.max_acceleration:5.1f}  braking max {check.max_braking:6.1f} "
        f"(over limit {check.hard_stops})  "
        f"reaction max {max(reactions) if reactions else 0:4.2f}s (n={len(reactions)})  "
        f"free-road stops {check.free_road_stops}  overlaps {check.overlaps}  "
        f"standing gap {min(gaps) if gaps else 0:.0f}-{max(gaps) if gaps else 0:.0f}px"
    )
    return ok, line


def main():
    with Pool(min(len(CASES), max(1, (os.cpu_count() or 2) - 2))) as pool:
        results = pool.map(evaluate, CASES)

    for _ok, line in results:
        print(line)

    failed = any(not ok for ok, _line in results)
    print("\nRESULT:", "FAIL" if failed else "OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
