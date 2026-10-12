"""Trains the vehicle detector on the dataset built from the simulation.

Usage:
    python tools/generate_detection_dataset.py
    python tools/train_detector.py
    python tools/train_detector.py --epochs 60 --batch 4

Needs the packages in requirements-yolo.txt. Writes the best weights to
weights/vehicle_detector.pt and the validation metrics to
reports/detector/metrics.json.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.camera import CLASS_NAMES  # noqa: E402

DATASET = PROJECT_ROOT / "data" / "detection_dataset" / "dataset.yaml"
WEIGHTS = PROJECT_ROOT / "weights" / "vehicle_detector.pt"
REPORT_DIR = PROJECT_ROOT / "reports" / "detector"
# Vehicles are about 25x50 px in the 900 px frame, so the frame is not
# downscaled for training.
IMAGE_SIZE = 896


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="yolo11n.pt")
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default="0")
    args = parser.parse_args()

    from ultralytics import YOLO

    model = YOLO(args.base)
    model.train(
        data=str(DATASET),
        imgsz=IMAGE_SIZE,
        epochs=args.epochs,
        batch=args.batch,
        device=args.device,
        project=str(PROJECT_ROOT / "runs"),
        name="vehicle_detector",
        exist_ok=True,
        seed=0,
        # The camera is fixed and overhead: vehicles appear in four
        # headings, so both flips are valid views.
        flipud=0.5,
        fliplr=0.5,
    )

    best = PROJECT_ROOT / "runs" / "vehicle_detector" / "weights" / "best.pt"
    WEIGHTS.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best, WEIGHTS)

    metrics = YOLO(str(WEIGHTS)).val(data=str(DATASET), imgsz=IMAGE_SIZE, device=args.device)
    summary = {
        "precision": round(float(metrics.box.mp), 4),
        "recall": round(float(metrics.box.mr), 4),
        "mAP50": round(float(metrics.box.map50), 4),
        "mAP50-95": round(float(metrics.box.map), 4),
        "per_class_mAP50-95": {
            CLASS_NAMES[int(index)]: round(float(value), 4)
            for index, value in zip(metrics.box.ap_class_index, metrics.box.maps[metrics.box.ap_class_index])
        },
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "metrics.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    print(f"-> {WEIGHTS}")


if __name__ == "__main__":
    main()
