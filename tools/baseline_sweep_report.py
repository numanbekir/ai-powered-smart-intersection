"""Summarise reports/baseline_sweep/raw_results.csv into a markdown table.

For every scenario: mean wait of each fixed-time green setting, the best
fixed setting, the best adaptive controller, and the adaptive gain measured
against (a) the default fixed green and (b) the best fixed green.

The wait used here covers every measured vehicle: the ones that crossed
(their full wait) and the ones still queued when the run ended (their wait
so far). Leaving the second group out would flatter whichever controller
leaves more vehicles behind.

Usage:
    python tools/baseline_sweep_report.py
"""
import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.run_batch_tests import SCENARIO_IDS  # noqa: E402

DEFAULT_INPUT = PROJECT_ROOT / "reports" / "baseline_sweep" / "raw_results.csv"
DEFAULT_GREEN = 10  # the fixed-time setting every scenario ships with
SHORT_NAMES = {
    "adaptive_ground_truth": "ground truth",
    "adaptive_camera": "camera",
}


def gain(baseline, value):
    if not baseline:
        return 0.0
    return (baseline - value) / baseline * 100.0


def all_vehicle_wait(row):
    measured = float(row["vehicles_measured"])
    uncrossed = float(row["vehicles_uncrossed"])
    if measured <= 0:
        return 0.0
    crossed = measured - uncrossed
    total = float(row["overall_avg_wait"]) * crossed + float(row["uncrossed_avg_wait"]) * uncrossed
    return total / measured


def load(path):
    runs = defaultdict(dict)  # (scenario, controller) -> seed -> metrics
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            measured = float(row["vehicles_measured"])
            runs[(row["scenario_id"], row["controller"])][int(row["seed"])] = {
                "wait": all_vehicle_wait(row),
                "delay": float(row["overall_avg_delay"]),
                "uncrossed_share": float(row["vehicles_uncrossed"]) / measured * 100.0 if measured else 0.0,
            }
    return runs


def avg(runs, key, metric):
    return mean(run[metric] for run in runs[key].values())


def build(runs):
    controllers = sorted({controller for _, controller in runs})
    fixed = sorted((c for c in controllers if c.startswith("fixed_g")), key=lambda c: int(c[7:]))
    adaptive = [c for c in controllers if not c.startswith("fixed_g")]
    default_fixed = f"fixed_g{DEFAULT_GREEN}"

    header = ["Scenario"] + [f"fixed {c[7:]}s" for c in fixed]
    header += ["best fixed", "best adaptive", f"gain (fixed {DEFAULT_GREEN}s)", "gain (best fixed)",
               "adaptive ahead (runs)", "not crossed: fixed / adaptive"]
    lines = ["| " + " | ".join(header) + " |", "|---|" + "---:|" * (len(header) - 1)]

    gains_default, gains_best, relative = [], [], defaultdict(list)
    clear_wins = 0
    for scenario in SCENARIO_IDS:
        if (scenario, default_fixed) not in runs:
            continue
        fixed_means = {c: avg(runs, (scenario, c), "wait") for c in fixed if (scenario, c) in runs}
        adaptive_means = {c: avg(runs, (scenario, c), "wait") for c in adaptive if (scenario, c) in runs}
        if not adaptive_means:
            continue
        best_fixed = min(fixed_means, key=fixed_means.get)
        best_adaptive = min(adaptive_means, key=adaptive_means.get)
        for controller, value in fixed_means.items():
            relative[controller].append(value / fixed_means[default_fixed])

        gain_default = gain(fixed_means[default_fixed], adaptive_means[best_adaptive])
        gain_best = gain(fixed_means[best_fixed], adaptive_means[best_adaptive])
        gains_default.append(gain_default)
        gains_best.append(gain_best)

        fixed_runs, adaptive_runs = runs[(scenario, best_fixed)], runs[(scenario, best_adaptive)]
        seeds = sorted(set(fixed_runs) & set(adaptive_runs))
        wins = sum(adaptive_runs[s]["wait"] < fixed_runs[s]["wait"] for s in seeds)
        if seeds and wins / len(seeds) >= 0.8:
            clear_wins += 1

        row = [scenario] + [f"{fixed_means[c]:.1f}" if c in fixed_means else "-" for c in fixed]
        row += [
            f"{best_fixed[7:]}s",
            f"{adaptive_means[best_adaptive]:.1f} ({SHORT_NAMES.get(best_adaptive, best_adaptive)})",
            f"{gain_default:.0f}%",
            f"{gain_best:.0f}%",
            f"{wins}/{len(seeds)}",
            f"{avg(runs, (scenario, best_fixed), 'uncrossed_share'):.0f}% / {avg(runs, (scenario, best_adaptive), 'uncrossed_share'):.0f}%",
        ]
        lines.append("| " + " | ".join(row) + " |")

    ordered = sorted(gains_best)
    median = ordered[len(ordered) // 2] if len(ordered) % 2 else (ordered[len(ordered) // 2 - 1] + ordered[len(ordered) // 2]) / 2
    summary = [
        f"- Scenarios: {len(gains_best)}",
        f"- Gain over the default fixed time ({DEFAULT_GREEN}s): mean {mean(gains_default):.0f}%, lowest {min(gains_default):.0f}%",
        f"- Gain over each scenario's best fixed time: median {median:.0f}%, mean {mean(gains_best):.0f}%, lowest {min(gains_best):.0f}%",
        f"- Scenarios where adaptive is ahead on average: {sum(g > 0 for g in gains_best)}/{len(gains_best)}",
        f"- Scenarios where adaptive is ahead in at least 80% of runs: {clear_wins}/{len(gains_best)}",
        "- If a single fixed time had to be picked (mean ratio to the default per scenario, lower is better): "
        + ", ".join(f"{c[7:]}s={mean(v):.3f}" for c, v in sorted(relative.items(), key=lambda kv: int(kv[0][7:]))),
    ]
    return lines, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    lines, summary = build(load(args.input))
    text = "# Fixed-time sweep and adaptive comparison\n\n"
    text += ("Average wait (s), mean over runs. Covers every measured vehicle: the wait of those that crossed "
             "and, for those still queued when the run ended, the wait up to that moment. Gain is the "
             "reduction in wait.\n\n")
    text += "\n".join(summary) + "\n\n" + "\n".join(lines) + "\n"

    output = args.output or args.input.with_name("summary.md")
    output.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
