import copy
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.result_registry import ResultRegistry
from core.scenario_registry import ScenarioRegistry
from core.controller_version_registry import ControllerVersionRegistry
from simulation.engine import SimulationEngine
from tools.report_generator import generate_report


BATCH_RUN_ID = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

SEEDS = [42, 101, 202, 303, 404, 505, 606, 707, 808, 909, 1111, 2222, 3333, 4444, 5555, 6666, 7777, 8888, 9999, 12345]

MIXED_MASTER_SEEDS = [42, 101, 202]

# 21 canonical scenarios + mixed_master_scenario -- matches the methodology
# used to validate fixed-vs-adaptive superiority and the ground-truth ceiling
# so batch results here stay directly comparable to those documented numbers.
# (demand_shift_traffic added post-recalibration to isolate demand-magnitude
# regime shifts from the directional shifts direction_shift_traffic tests --
# see docs/scenario_capacity_calibration.md.)
SCENARIO_IDS = [
    "balanced_traffic",
    "right_heavy_traffic",
    "vertical_heavy_traffic",
    "peak_traffic",
    "low_traffic",
    "turn_heavy_traffic",
    "single_direction_traffic",
    "extreme_directional_traffic",
    "sparse_traffic",
    "idle_intersection",
    "direction_shift_traffic",
    "demand_shift_traffic",
    "burst_traffic",
    "alternating_heavy_traffic",
    "asymmetric_peak_traffic",
    "turning_conflict_traffic",
    "emergency_balanced_traffic",
    "emergency_right_heavy_traffic",
    "emergency_peak_traffic",
    "emergency_sparse_traffic",
    "emergency_low_frequency_mixed_traffic",
    "mixed_master_scenario",
]

TEST_MATRIX = [
    {
        "mode": "fixed",
        "provider_id": "ground_truth_v1",
        "controller_version_id": None,
    },
    {
        "mode": "adaptive",
        "provider_id": "ground_truth_v1",
        "controller_version_id": "adaptive_optimal_ground_truth",
    },
    {
        "mode": "adaptive",
        "provider_id": "ground_truth_v1",
        "controller_version_id": "adaptive_optimal_ground_truth_v2",
    },
    {
        "mode": "adaptive",
        "provider_id": "ground_truth_v1",
        "controller_version_id": "adaptive_optimal_ground_truth_v3",
    },
    {
        "mode": "adaptive",
        "provider_id": "ground_truth_v1",
        "controller_version_id": "adaptive_rolling_horizon_ground_truth",
    },
    {
        "mode": "adaptive",
        "provider_id": "ground_truth_v1",
        "controller_version_id": "adaptive_rolling_horizon_ground_truth_v2",
    },
]


def build_test_name(
    batch_run_id,
    scenario_name,
    mode,
    provider_id,
    controller_version_id,
    seed,
):
    clean_scenario = scenario_name.lower().replace(" ", "_").replace("-", "_")
    controller_part = controller_version_id or "fixed_baseline"

    return (
        f"{batch_run_id}"
        f"__{clean_scenario}"
        f"__{mode}"
        f"__{provider_id}"
        f"__{controller_part}"
        f"__seed_{seed}"
    )


def attach_batch_metadata(result, batch_run_id):
    result["batch_identity"] = {
        "batch_run_id": batch_run_id,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "runner": "tools/run_batch_tests.py",
    }
    return result


def get_scenario_emergency_label(scenario):
    emergency = scenario.get("config", {}).get("emergency", {})
    enabled = emergency.get("enabled", False)
    priority_enabled = emergency.get("priority_enabled", False)

    if enabled and priority_enabled:
        return "ON + PRIORITY"

    if enabled:
        return "ON"

    return "OFF"


def seeds_for_scenario(scenario_id):
    # mixed_master_scenario is a 30-minute stress test; running it with the
    # full 20-seed matrix would be prohibitively slow, so it uses a smaller
    # seed set.
    if scenario_id == "mixed_master_scenario":
        return MIXED_MASTER_SEEDS
    return SEEDS


def main():
    scenario_registry = ScenarioRegistry()
    controller_registry = ControllerVersionRegistry()
    result_registry = ResultRegistry()

    total_runs = sum(
        len(seeds_for_scenario(scenario_id)) * len(TEST_MATRIX)
        for scenario_id in SCENARIO_IDS
    )
    run_index = 0

    print("=" * 80)
    print("HEADLESS BATCH TEST RUNNER STARTED")
    print(f"Batch Run ID: {BATCH_RUN_ID}")
    print(f"Total planned runs: {total_runs}")
    print("Playback speed override: 8.0x")
    print("Emergency: scenario-config")
    print("=" * 80)

    for scenario_id in SCENARIO_IDS:
        base_scenario = scenario_registry.get_by_id(scenario_id)

        if not base_scenario:
            print(f"[SKIP] Scenario not found: {scenario_id}")
            continue

        print(
            f"[SCENARIO] {scenario_id} | "
            f"Emergency: {get_scenario_emergency_label(base_scenario)}"
        )

        for test_config in TEST_MATRIX:
            mode = test_config["mode"]
            provider_id = test_config["provider_id"]
            controller_version_id = test_config["controller_version_id"]

            controller_version = None

            if mode == "adaptive":
                controller_version = controller_registry.get(controller_version_id)

                if not controller_version:
                    print(f"[SKIP] Controller version not found: {controller_version_id}")
                    continue

            for seed in seeds_for_scenario(scenario_id):
                run_index += 1

                scenario = copy.deepcopy(base_scenario)
                scenario["config"]["random_seed"] = seed
                scenario["config"]["playback_speed"] = 8.0

                test_name = build_test_name(
                    batch_run_id=BATCH_RUN_ID,
                    scenario_name=scenario["scenario_name"],
                    mode=mode,
                    provider_id=provider_id,
                    controller_version_id=controller_version_id,
                    seed=seed,
                )

                print("-" * 80)
                print(f"[{run_index}/{total_runs}] {test_name}")
                print(f"Emergency: {get_scenario_emergency_label(scenario)}")

                try:
                    engine = SimulationEngine(
                        scenario=scenario,
                        test_name=test_name,
                        controller_mode=mode,
                        controller_version=controller_version,
                        state_provider_id=provider_id,
                        headless=True,
                    )

                    outcome = engine.run()
                    result = outcome.get("result")

                    if not result:
                        print("[WARN] No result returned.")
                        continue

                    result = attach_batch_metadata(result, BATCH_RUN_ID)

                    if result.get("interrupted", False):
                        print(
                            "[WARN] Interrupted result returned. "
                            "It will be saved but ignored in reports."
                        )

                    result_registry.add(result)

                    metrics = result["metrics"]

                    print(
                        f"[OK] "
                        f"avg_wait={metrics['overall_avg_wait']:.2f} | "
                        f"max_wait={metrics['overall_max_wait']:.2f} | "
                        f"queue_peak={metrics['queue_length_peak']} | "
                        f"crossed={metrics['total_crossed']} | "
                        f"emg_spawned={metrics.get('emergency_spawned', 0)} | "
                        f"emg_crossed={metrics.get('emergency_crossed', 0)} | "
                        f"emg_avg={metrics.get('emergency_avg_wait', 0):.2f} | "
                        f"emg_max={metrics.get('emergency_max_wait', 0):.2f} | "
                        f"priority={metrics.get('priority_activation_count', 0)}"
                    )

                except Exception as e:
                    print(f"[ERROR] {test_name}: {e}")

    print("=" * 80)
    print("HEADLESS BATCH TEST RUNNER FINISHED")
    print("=" * 80)

    print("=" * 80)
    print("GENERATING REPORT")
    print("=" * 80)

    generate_report(batch_run_id=BATCH_RUN_ID)


if __name__ == "__main__":
    main()