import copy
import json
import sys
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.scenario_registry import ScenarioRegistry
from core.controller_version_registry import ControllerVersionRegistry
from simulation.engine import SimulationEngine


def run_once(base_scenario, controller_version, seed, inject_load=False):
    scenario = copy.deepcopy(base_scenario)
    scenario["config"]["random_seed"] = seed
    scenario["config"]["playback_speed"] = 8.0
    scenario["config"]["simulation_time"] = 25

    stop_load = threading.Event()
    load_thread = None

    if inject_load:
        def burn_cpu():
            while not stop_load.is_set():
                sum(i * i for i in range(200_000))

        load_thread = threading.Thread(target=burn_cpu, daemon=True)
        load_thread.start()

    engine = SimulationEngine(
        scenario=scenario,
        test_name="determinism_check",
        controller_mode="adaptive",
        controller_version=controller_version,
        state_provider_id="ground_truth_v1",
        headless=True,
    )

    outcome = engine.run()

    if load_thread:
        stop_load.set()
        load_thread.join(timeout=1)

    return outcome["result"]


def strip_volatile(result):
    result = copy.deepcopy(result)
    result.pop("timestamp", None)
    return result


def compare(label, result_a, result_b, verbose=True):
    a_json = json.dumps(strip_volatile(result_a), sort_keys=True, default=str)
    b_json = json.dumps(strip_volatile(result_b), sort_keys=True, default=str)

    if a_json == b_json:
        if verbose:
            print(f"[{label}] IDENTICAL")
        return True

    print(f"[{label}] DIVERGED")

    metrics_a = result_a.get("metrics", {})
    metrics_b = result_b.get("metrics", {})
    for key in sorted(set(metrics_a) | set(metrics_b)):
        va, vb = metrics_a.get(key), metrics_b.get(key)
        if va != vb:
            print(f"  metrics.{key}: A={va}  B={vb}")

    log_a = result_a.get("decision_log", [])
    log_b = result_b.get("decision_log", [])
    for i, (ea, eb) in enumerate(zip(log_a, log_b)):
        if ea != eb:
            print(f"  decision_log[{i}] diverged:")
            print(f"    A={ea}")
            print(f"    B={eb}")
            break
    if len(log_a) != len(log_b):
        print(f"  decision_log length: A={len(log_a)}  B={len(log_b)}")

    return False


def main():
    scenario_registry = ScenarioRegistry()
    controller_registry = ControllerVersionRegistry()

    base_scenario = scenario_registry.get_by_id("peak_traffic")
    controller_version = controller_registry.get("adaptive_optimal_ground_truth")
    seed = 42

    print("=" * 70)
    print("DETERMINISM CHECK: peak_traffic / adaptive_optimal_ground_truth / seed=42")
    print("=" * 70)

    print("\n[1] Same seed, no artificial load, run twice:")
    result_a1 = run_once(base_scenario, controller_version, seed, inject_load=False)
    result_a2 = run_once(base_scenario, controller_version, seed, inject_load=False)
    ok_baseline = compare("no-load repeat", result_a1, result_a2)

    print("\n[2] Same seed, second run has artificial CPU load injected:")
    result_b1 = run_once(base_scenario, controller_version, seed, inject_load=False)
    result_b2 = run_once(base_scenario, controller_version, seed, inject_load=True)
    ok_loaded = compare("load-injected vs clean", result_b1, result_b2)

    print("\n" + "=" * 70)
    print("OVERALL:", "IDENTICAL" if (ok_baseline and ok_loaded) else "DIVERGED")
    print("=" * 70)

    return 0 if (ok_baseline and ok_loaded) else 1


if __name__ == "__main__":
    sys.exit(main())
