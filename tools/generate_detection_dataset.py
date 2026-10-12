"""Builds a vehicle detection dataset from the simulation itself.

Runs scenarios headless, saves the overhead camera frame every few
simulated seconds and writes the matching YOLO labels from the known
vehicle positions. No manual labelling is involved.

Usage:
    python tools/generate_detection_dataset.py
    python tools/generate_detection_dataset.py --interval 3 --sim-time 240

Writes data/detection_dataset/ (images/, labels/, dataset.yaml).
Train with tools/train_detector.py.
"""
import argparse
import copy
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from core.scenario_registry import ScenarioRegistry  # noqa: E402
from simulation.camera import CLASS_NAMES, FRAME_SIZE, IntersectionCamera  # noqa: E402
from simulation.engine import SimulationEngine  # noqa: E402

OUTPUT_DIR = PROJECT_ROOT / "data" / "detection_dataset"
# (scenario, seed, split). Validation runs use scenarios and seeds the
# training runs never see.
RUNS = [
    ("balanced_traffic", 11, "train"),
    ("peak_traffic", 12, "train"),
    ("right_heavy_traffic", 13, "train"),
    ("turn_heavy_traffic", 14, "train"),
    ("low_traffic", 15, "train"),
    ("asymmetric_peak_traffic", 16, "train"),
    ("emergency_peak_traffic", 17, "train"),
    ("emergency_right_heavy_traffic", 18, "train"),
    ("vertical_heavy_traffic", 21, "val"),
    ("burst_traffic", 22, "val"),
    ("emergency_balanced_traffic", 23, "val"),
]
PLAYBACK_SPEED = 8.0


def capture_run(scenario_id, seed, split, sim_time, interval):
    scenario = copy.deepcopy(ScenarioRegistry().get_by_id(scenario_id))
    config = scenario["config"]
    config["random_seed"] = seed
    config["playback_speed"] = PLAYBACK_SPEED
    config["simulation_time"] = sim_time
    # Every class has to appear in the dataset, whatever the scenario allows.
    config["allowed_vehicle_types"] = {name: True for name in ["car", "bus", "truck", "bike"]}
    for distribution in config["road_vehicle_distribution"].values():
        distribution.update({"car": 40, "bus": 20, "truck": 20, "bike": 20})
    config["emergency"]["enabled"] = True
    config["emergency"]["spawn_probability"] = 0.25
    config["emergency"]["min_spawn_gap"] = 6
    config["emergency"]["max_active_emergency"] = 3

    engine = SimulationEngine(
        scenario=scenario,
        test_name=f"detection_dataset__{scenario_id}__seed_{seed}",
        controller_mode="fixed",
        state_provider_id="ground_truth_v1",
        headless=True,
    )
    camera = IntersectionCamera(engine)
    image_dir = OUTPUT_DIR / "images" / split
    label_dir = OUTPUT_DIR / "labels" / split
    image_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)
    state = {"next": interval, "frames": 0, "boxes": 0}

    def capture(engine):
        if engine.simulation_elapsed < state["next"]:
            return
        state["next"] += interval
        stem = f"{scenario_id}_s{seed}_{state['frames']:04d}"
        pygame.image.save(camera.render(), str(image_dir / f"{stem}.png"))
        lines = []
        for name, x1, y1, x2, y2 in camera.vehicle_boxes():
            lines.append(
                f"{CLASS_NAMES.index(name)} {(x1 + x2) / 2 / FRAME_SIZE:.6f} "
                f"{(y1 + y2) / 2 / FRAME_SIZE:.6f} {(x2 - x1) / FRAME_SIZE:.6f} "
                f"{(y2 - y1) / FRAME_SIZE:.6f}"
            )
        (label_dir / f"{stem}.txt").write_text("\n".join(lines) + ("\n" if lines else ""))
        state["frames"] += 1
        state["boxes"] += len(lines)

    engine.tick_listeners.append(capture)
    engine.run()
    return state["frames"], state["boxes"]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sim-time", type=float, default=300.0)
    parser.add_argument("--interval", type=float, default=2.0, help="simulated seconds between frames")
    args = parser.parse_args()

    for scenario_id, seed, split in RUNS:
        frames, boxes = capture_run(scenario_id, seed, split, args.sim_time, args.interval)
        print(f"{split:5s} {scenario_id:32s} {frames:4d} frames {boxes:5d} boxes", flush=True)

    (OUTPUT_DIR / "dataset.yaml").write_text(
        f"path: {OUTPUT_DIR}\ntrain: images/train\nval: images/val\nnames:\n"
        + "".join(f"  {index}: {name}\n" for index, name in enumerate(CLASS_NAMES))
    )
    print(f"-> {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
