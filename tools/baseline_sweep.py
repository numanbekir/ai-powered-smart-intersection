"""Fixed-time green sweep, with the adaptive controllers run alongside.

Re-runs the fixed-time baseline with several green durations on every
scenario, and the adaptive controllers on the same seeds with the same
engine, so adaptive control is compared against the best fixed-time
setting instead of a single hand-picked one.

Usage:
    python tools/baseline_sweep.py                  # full sweep
    python tools/baseline_sweep.py --workers 8
    python tools/baseline_sweep.py --greens 6 8 10 --scenarios balanced_traffic

Writes reports/baseline_sweep/raw_results.csv (one row per run).
Summarise with tools/baseline_sweep_report.py.
"""
import argparse
import copy
import csv
import multiprocessing as mp
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.run_batch_tests import SCENARIO_IDS, seeds_for_scenario  # noqa: E402

DEFAULT_GREENS = [5, 6, 8, 10, 12]
DEFAULT_ADAPTIVE = [
    "adaptive_optimal_ground_truth_v3",
    "adaptive_rolling_horizon_ground_truth",
]
DEFAULT_SEEDS = [42, 101, 202, 303, 404, 505, 606, 707, 808, 909]
# The scenarios ship with 120 s runs, which mostly measure the start-up
# transient of an empty intersection. For measurement every scenario is run
# for SIM_TIME with the first WARMUP seconds left out of the statistics.
# mixed_master_scenario keeps its own (30 min) duration.
SIM_TIME = 600.0
WARMUP = 120.0
PLAYBACK_SPEED = 8.0  # same as tools/run_batch_tests.py, keeps metrics comparable
OUTPUT_DIR = PROJECT_ROOT / "reports" / "baseline_sweep"
METRIC_KEYS = [
    "overall_avg_wait",
    "overall_avg_delay",
    "overall_delay_p95",
    "vehicles_measured",
    "vehicles_uncrossed",
    "uncrossed_avg_wait",
    "emergency_spawned",
    "emergency_hold_count",
    "overall_wait_p95",
    "overall_wait_p99",
    "overall_max_wait",
    "total_crossed",
    "queue_length_average",
    "queue_length_peak",
    "emergency_avg_wait",
]


def run_one(task):
    scenario_id, mode, setting, seed, sim_time, warmup = task
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    from core.controller_version_registry import ControllerVersionRegistry
    from core.scenario_registry import ScenarioRegistry
    from simulation.engine import SimulationEngine

    scenario = copy.deepcopy(ScenarioRegistry().get_by_id(scenario_id))
    config = scenario["config"]
    config["random_seed"] = seed
    config["playback_speed"] = PLAYBACK_SPEED
    config["warmup_time"] = warmup
    if scenario_id != "mixed_master_scenario":
        config["simulation_time"] = sim_time

    controller_version = None
    state_provider_id = "ground_truth_v1"
    if mode == "fixed":
        yellow_time = config["fixed"]["yellow_time"]
        config["fixed"]["green_time"] = setting
        # Three other approaches are served before this one comes back.
        config["fixed"]["red_time"] = 3 * (setting + yellow_time)
        controller = f"fixed_g{setting}"
    else:
        controller_version = ControllerVersionRegistry().get(setting)
        controller = setting
        if controller_version.get("target_state_provider_type") == "yolo":
            state_provider_id = "yolo_v1"

    engine = SimulationEngine(
        scenario=scenario,
        test_name=f"baseline_sweep__{scenario_id}__{controller}__seed_{seed}",
        controller_mode=mode,
        controller_version=controller_version,
        state_provider_id=state_provider_id,
        headless=True,
    )
    metrics = engine.run()["result"].get("metrics", {})

    row = {
        "scenario_id": scenario_id,
        "mode": mode,
        "controller": controller,
        "green_time": setting if mode == "fixed" else "",
        "seed": seed,
    }
    for key in METRIC_KEYS:
        row[key] = metrics.get(key)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--greens", type=int, nargs="*", default=DEFAULT_GREENS)
    parser.add_argument("--adaptive", nargs="*", default=DEFAULT_ADAPTIVE)
    parser.add_argument("--scenarios", nargs="+", default=SCENARIO_IDS)
    parser.add_argument("--seeds", type=int, nargs="+", default=None)
    parser.add_argument("--sim-time", type=float, default=SIM_TIME)
    parser.add_argument("--warmup", type=float, default=WARMUP)
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR / "raw_results.csv")
    args = parser.parse_args()

    settings = [("fixed", green) for green in args.greens]
    settings += [("adaptive", version_id) for version_id in args.adaptive]

    tasks = [
        (scenario_id, mode, setting, seed, args.sim_time, args.warmup)
        for scenario_id in args.scenarios
        for mode, setting in settings
        for seed in (args.seeds or (seeds_for_scenario(scenario_id) if scenario_id == "mixed_master_scenario" else DEFAULT_SEEDS))
    ]
    # Longest runs first so the pool does not end on a single slow straggler.
    tasks.sort(key=lambda t: t[0] != "mixed_master_scenario")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    print(f"{len(tasks)} runs, {args.workers} workers -> {args.output}")

    fieldnames = ["scenario_id", "mode", "controller", "green_time", "seed"] + METRIC_KEYS
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        with mp.get_context("spawn").Pool(args.workers) as pool:
            for done, row in enumerate(pool.imap_unordered(run_one, tasks), start=1):
                writer.writerow(row)
                handle.flush()
                if done % 100 == 0 or done == len(tasks):
                    print(f"[{done}/{len(tasks)}]", flush=True)


if __name__ == "__main__":
    main()
