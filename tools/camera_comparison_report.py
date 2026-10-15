"""Fixed time vs ground-truth adaptive vs camera-based adaptive.

Joins reports/baseline_sweep/raw_results.csv (fixed-time sweep and the
ground-truth controller) with reports/camera/raw_results.csv (the same
scenarios and seeds run with the YOLO state provider) and writes
reports/camera/summary.md.

Usage:
    python tools/baseline_sweep.py
    python tools/baseline_sweep.py --greens --adaptive adaptive_camera \\
        --workers 8 --output reports/camera/raw_results.csv
    python tools/camera_comparison_report.py
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.baseline_sweep_report import all_vehicle_wait, gain  # noqa: E402
from tools.run_batch_tests import SCENARIO_IDS  # noqa: E402

BASELINE = PROJECT_ROOT / "reports" / "baseline_sweep" / "raw_results.csv"
CAMERA = PROJECT_ROOT / "reports" / "camera" / "raw_results.csv"
OUTPUT = PROJECT_ROOT / "reports" / "camera" / "summary.md"
GROUND_TRUTH = "adaptive_ground_truth"
CAMERA_CONTROLLER = "adaptive_camera"


def load(path, runs):
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            measured = float(row["vehicles_measured"])
            runs[(row["scenario_id"], row["controller"])][int(row["seed"])] = {
                "wait": all_vehicle_wait(row),
                "uncrossed": float(row["vehicles_uncrossed"]) / measured * 100.0 if measured else 0.0,
                "emergency_wait": float(row["emergency_avg_wait"] or 0.0),
                "emergency_spawned": float(row["emergency_spawned"] or 0.0),
            }


def main():
    runs = defaultdict(dict)
    load(BASELINE, runs)
    load(CAMERA, runs)

    lines = [
        "| Senaryo | en iyi sabit | tam bilgi | kamera | kamera kazancı (en iyi sabit) | kameranın tam bilgiye göre kaybı | kamera önde (koşu) | geçemeyen: tam bilgi / kamera |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    emergency_lines = [
        "| Senaryo | en iyi sabit | tam bilgi | kamera |",
        "|---|---:|---:|---:|",
    ]
    gains, losses, ahead = [], [], 0

    for scenario in SCENARIO_IDS:
        camera = runs.get((scenario, CAMERA_CONTROLLER))
        truth = runs.get((scenario, GROUND_TRUTH))
        if not camera or not truth:
            continue
        seeds = sorted(camera)
        fixed = {
            controller: by_seed
            for (name, controller), by_seed in runs.items()
            if name == scenario and controller.startswith("fixed_g")
        }
        best_fixed = min(fixed, key=lambda c: mean(fixed[c][s]["wait"] for s in seeds))

        def avg(by_seed, key="wait"):
            return mean(by_seed[s][key] for s in seeds)

        fixed_wait, truth_wait, camera_wait = avg(fixed[best_fixed]), avg(truth), avg(camera)
        camera_gain = gain(fixed_wait, camera_wait)
        loss = camera_wait - truth_wait
        wins = sum(1 for s in seeds if camera[s]["wait"] < fixed[best_fixed][s]["wait"])
        gains.append(camera_gain)
        losses.append(loss)
        ahead += camera_wait < fixed_wait

        lines.append(
            f"| {scenario} | {fixed_wait:.1f} ({best_fixed.replace('fixed_g', '')}s) | {truth_wait:.1f} | "
            f"{camera_wait:.1f} | %{camera_gain:.0f} | {loss:+.1f} sn | {wins}/{len(seeds)} | "
            f"%{avg(truth, 'uncrossed'):.0f} / %{avg(camera, 'uncrossed'):.0f} |"
        )

        if avg(camera, "emergency_spawned") > 0:
            emergency_lines.append(
                f"| {scenario} | {avg(fixed[best_fixed], 'emergency_wait'):.1f} | "
                f"{avg(truth, 'emergency_wait'):.1f} | {avg(camera, 'emergency_wait'):.1f} |"
            )

    summary = [
        "# Sabit süre, tam bilgili adaptif ve kameralı adaptif",
        "",
        "Ortalama bekleme süresi (sn), ölçüme giren tüm araçlar. Üç kontrolcü aynı senaryo ve tohumlarla koşuldu.",
        "Kameralı kontrolcü tam bilgili kontrolcüyle aynı karar kuralını kullanır, girdisi yalnızca YOLO tespitleridir.",
        "",
        f"- Kameralı kontrolün en iyi sabit süreye göre kazancı: ortanca %{median(gains):.0f}, ortalama %{mean(gains):.0f}, en düşük %{min(gains):.0f}",
        f"- Kameralı kontrolün ortalamada sabit sürenin önünde olduğu senaryo: {ahead}/{len(gains)}",
        f"- Tam bilgiye göre kayıp (kamera eksi tam bilgi): ortanca {median(losses):+.1f} sn, en yüksek {max(losses):+.1f} sn",
        "",
        *lines,
        "",
        "## Acil durum araçlarının ortalama beklemesi (sn)",
        "",
        *emergency_lines,
        "",
    ]
    OUTPUT.write_text("\n".join(summary), encoding="utf-8")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
