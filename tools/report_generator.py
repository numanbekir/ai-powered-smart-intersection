import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean, pstdev

import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_INDEX_FILE = PROJECT_ROOT / "data" / "results_index.json"
BATCHES_DIR = PROJECT_ROOT / "data" / "batches"
REPORTS_ROOT = PROJECT_ROOT / "reports"


def load_results(batch_run_id=None):
    results = []

    if batch_run_id:
        batch_file = BATCHES_DIR / f"{batch_run_id}.jsonl"

        if not batch_file.exists():
            return []

        with open(batch_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if not line:
                    continue

                try:
                    result = json.loads(line)

                    if not result.get("interrupted", False):
                        results.append(result)

                except Exception:
                    continue

        return results

    if not RESULTS_INDEX_FILE.exists():
        return []

    with open(RESULTS_INDEX_FILE, "r", encoding="utf-8") as f:
        index = json.load(f)

    batch_files = sorted({
        row.get("batch_file")
        for row in index
        if row.get("batch_file")
    })

    for relative_path in batch_files:
        batch_file = PROJECT_ROOT / "data" / relative_path

        if not batch_file.exists():
            continue

        with open(batch_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if not line:
                    continue

                try:
                    result = json.loads(line)

                    if not result.get("interrupted", False):
                        results.append(result)

                except Exception:
                    continue

    return results


def get_provider_type(provider_id):
    if provider_id.startswith("ground_truth"):
        return "ground_truth"
    if provider_id.startswith("visible_area"):
        return "visible_area"
    if provider_id.startswith("yolo"):
        return "yolo"
    return provider_id


def get_group_key(result):
    exp = result.get("experiment_identity", {})

    return (
        exp.get("scenario_id", "-"),
        exp.get("controller_mode", "-"),
        exp.get("controller_version_id", "fixed_baseline"),
        get_provider_type(exp.get("state_provider_id", "-")),
    )


def summarize_group(items):
    avg_waits = [r["metrics"]["overall_avg_wait"] for r in items]
    median_waits = [r["metrics"].get("overall_median_wait", 0) for r in items]
    max_waits = [r["metrics"]["overall_max_wait"] for r in items]

    wait_p50 = [r["metrics"].get("overall_wait_p50", 0) for r in items]
    wait_p90 = [r["metrics"].get("overall_wait_p90", 0) for r in items]
    wait_p95 = [r["metrics"].get("overall_wait_p95", 0) for r in items]
    wait_p99 = [r["metrics"].get("overall_wait_p99", 0) for r in items]

    queue_avgs = [r["metrics"].get("queue_length_average", 0) for r in items]
    queue_peaks = [r["metrics"]["queue_length_peak"] for r in items]
    crossed = [r["metrics"]["total_crossed"] for r in items]

    emergency_spawned = [r["metrics"].get("emergency_spawned", 0) for r in items]
    emergency_crossed = [r["metrics"].get("emergency_crossed", 0) for r in items]
    emergency_avg_wait = [r["metrics"].get("emergency_avg_wait", 0) for r in items]
    emergency_max_wait = [r["metrics"].get("emergency_max_wait", 0) for r in items]
    emergency_wait_p95 = [r["metrics"].get("emergency_wait_p95", 0) for r in items]
    emergency_wait_p99 = [r["metrics"].get("emergency_wait_p99", 0) for r in items]

    normal_vehicle_avg_wait = [r["metrics"].get("normal_vehicle_avg_wait", 0) for r in items]
    normal_vehicle_p95_wait = [r["metrics"].get("normal_vehicle_p95_wait", 0) for r in items]

    priority_activation_count = [
        r["metrics"].get("priority_activation_count", 0)
        for r in items
    ]

    emergency_hold_count = [
        r["metrics"].get("emergency_hold_count", 0)
        for r in items
    ]

    emergency_total_hold_time = [
        r["metrics"].get("emergency_total_hold_time", 0)
        for r in items
    ]

    emergency_hold_max_time = [
        r["metrics"].get("emergency_hold_max_time", 0)
        for r in items
    ]

    emergency_hold_success_count = [
        r["metrics"].get("emergency_hold_success_count", 0)
        for r in items
    ]

    return {
        "test_count": len(items),
        "avg_wait_mean": round(mean(avg_waits), 3),
        "avg_wait_std": round(pstdev(avg_waits), 3) if len(avg_waits) > 1 else 0.0,
        "median_wait_mean": round(mean(median_waits), 3),
        "max_wait_mean": round(mean(max_waits), 3),
        "wait_p50_mean": round(mean(wait_p50), 3),
        "wait_p90_mean": round(mean(wait_p90), 3),
        "wait_p95_mean": round(mean(wait_p95), 3),
        "wait_p99_mean": round(mean(wait_p99), 3),
        "queue_avg_mean": round(mean(queue_avgs), 3),
        "queue_peak_mean": round(mean(queue_peaks), 3),
        "total_crossed_mean": round(mean(crossed), 3),
        "emergency_spawned_mean": round(mean(emergency_spawned), 3),
        "emergency_crossed_mean": round(mean(emergency_crossed), 3),
        "emergency_avg_wait_mean": round(mean(emergency_avg_wait), 3),
        "emergency_max_wait_mean": round(mean(emergency_max_wait), 3),
        "emergency_wait_p95_mean": round(mean(emergency_wait_p95), 3),
        "emergency_wait_p99_mean": round(mean(emergency_wait_p99), 3),
        "normal_vehicle_avg_wait_mean": round(mean(normal_vehicle_avg_wait), 3),
        "normal_vehicle_p95_wait_mean": round(mean(normal_vehicle_p95_wait), 3),
        "priority_activation_count_mean": round(mean(priority_activation_count), 3),
        "emergency_hold_count_mean": round(mean(emergency_hold_count), 3),
        "emergency_total_hold_time_mean": round(mean(emergency_total_hold_time), 3),
        "emergency_hold_max_time_mean": round(mean(emergency_hold_max_time), 3),
        "emergency_hold_success_count_mean": round(mean(emergency_hold_success_count), 3),
    }


def add_fixed_comparison_metrics(summaries):
    fixed_by_scenario = {}

    for key, summary in summaries.items():
        scenario_id, mode, _controller_version, _provider_type = key
        if mode == "fixed":
            fixed_by_scenario[scenario_id] = summary

    for key, summary in summaries.items():
        scenario_id, mode, _controller_version, _provider_type = key
        fixed = fixed_by_scenario.get(scenario_id)

        summary["avg_wait_improvement_pct"] = 0.0
        summary["throughput_change_pct"] = 0.0
        summary["queue_peak_change_pct"] = 0.0
        summary["p95_wait_improvement_pct"] = 0.0
        summary["p99_wait_improvement_pct"] = 0.0
        summary["max_wait_improvement_pct"] = 0.0
        summary["stability_score"] = round(summary["avg_wait_std"], 3)

        if not fixed or mode == "fixed":
            continue

        fixed_avg_wait = fixed["avg_wait_mean"]
        fixed_crossed = fixed["total_crossed_mean"]
        fixed_queue_peak = fixed["queue_peak_mean"]
        fixed_p95 = fixed.get("wait_p95_mean", 0)
        fixed_p99 = fixed.get("wait_p99_mean", 0)
        fixed_max_wait = fixed.get("max_wait_mean", 0)

        if fixed_avg_wait > 0:
            summary["avg_wait_improvement_pct"] = round(
                ((fixed_avg_wait - summary["avg_wait_mean"]) / fixed_avg_wait) * 100,
                2,
            )

        if fixed_crossed > 0:
            summary["throughput_change_pct"] = round(
                ((summary["total_crossed_mean"] - fixed_crossed) / fixed_crossed) * 100,
                2,
            )

        if fixed_queue_peak > 0:
            summary["queue_peak_change_pct"] = round(
                ((fixed_queue_peak - summary["queue_peak_mean"]) / fixed_queue_peak) * 100,
                2,
            )

        if fixed_p95 > 0:
            summary["p95_wait_improvement_pct"] = round(
                ((fixed_p95 - summary["wait_p95_mean"]) / fixed_p95) * 100,
                2,
            )

        if fixed_p99 > 0:
            summary["p99_wait_improvement_pct"] = round(
                ((fixed_p99 - summary["wait_p99_mean"]) / fixed_p99) * 100,
                2,
            )

        if fixed_max_wait > 0:
            summary["max_wait_improvement_pct"] = round(
                ((fixed_max_wait - summary["max_wait_mean"]) / fixed_max_wait) * 100,
                2,
            )


def build_output_dir(batch_run_id=None):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if batch_run_id:
        output_dir = REPORTS_ROOT / f"{batch_run_id}_report_{timestamp}"
    else:
        output_dir = REPORTS_ROOT / f"batch_report_{timestamp}"

    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_raw_csv(results, output_dir):
    path = output_dir / "raw_results.csv"

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow([
            "batch_run_id",
            "timestamp",
            "test_name",
            "scenario_id",
            "scenario_name",
            "seed",
            "mode",
            "controller_version",
            "provider_id",
            "provider_type",
            "avg_wait",
            "median_wait",
            "max_wait",
            "wait_p50",
            "wait_p90",
            "wait_p95",
            "wait_p99",
            "queue_avg",
            "queue_peak",
            "total_crossed",
            "emergency_spawned",
            "emergency_crossed",
            "emergency_avg_wait",
            "emergency_max_wait",
            "emergency_wait_p95",
            "emergency_wait_p99",
            "normal_vehicle_crossed",
            "normal_vehicle_avg_wait",
            "normal_vehicle_p95_wait",
            "priority_activation_count",
            "emergency_hold_count",
            "emergency_total_hold_time",
            "emergency_hold_max_time",
            "emergency_hold_success_count",
        ])

        for r in results:
            exp = r.get("experiment_identity", {})
            test = r.get("test_identity", {})
            metrics = r.get("metrics", {})
            provider_id = exp.get("state_provider_id", "-")

            writer.writerow([
                r.get("batch_identity", {}).get("batch_run_id", "-"),
                r.get("timestamp", "-"),
                test.get("test_name", "-"),
                exp.get("scenario_id", "-"),
                test.get("scenario_name", "-"),
                test.get("seed", "-"),
                exp.get("controller_mode", "-"),
                exp.get("controller_version_id", "-"),
                provider_id,
                get_provider_type(provider_id),
                metrics.get("overall_avg_wait", 0),
                metrics.get("overall_median_wait", 0),
                metrics.get("overall_max_wait", 0),
                metrics.get("overall_wait_p50", 0),
                metrics.get("overall_wait_p90", 0),
                metrics.get("overall_wait_p95", 0),
                metrics.get("overall_wait_p99", 0),
                metrics.get("queue_length_average", 0),
                metrics.get("queue_length_peak", 0),
                metrics.get("total_crossed", 0),
                metrics.get("emergency_spawned", 0),
                metrics.get("emergency_crossed", 0),
                metrics.get("emergency_avg_wait", 0),
                metrics.get("emergency_max_wait", 0),
                metrics.get("emergency_wait_p95", 0),
                metrics.get("emergency_wait_p99", 0),
                metrics.get("normal_vehicle_crossed", 0),
                metrics.get("normal_vehicle_avg_wait", 0),
                metrics.get("normal_vehicle_p95_wait", 0),
                metrics.get("priority_activation_count", 0),
                metrics.get("emergency_hold_count", 0),
                metrics.get("emergency_total_hold_time", 0),
                metrics.get("emergency_hold_max_time", 0),
                metrics.get("emergency_hold_success_count", 0),
            ])

    return path


def write_summary_csv(summaries, output_dir):
    path = output_dir / "summary_by_group.csv"

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow([
            "scenario_id",
            "mode",
            "controller_version",
            "provider_type",
            "test_count",
            "avg_wait_mean",
            "avg_wait_std",
            "median_wait_mean",
            "max_wait_mean",
            "wait_p50_mean",
            "wait_p90_mean",
            "wait_p95_mean",
            "wait_p99_mean",
            "queue_avg_mean",
            "queue_peak_mean",
            "total_crossed_mean",
            "emergency_spawned_mean",
            "emergency_crossed_mean",
            "emergency_avg_wait_mean",
            "emergency_max_wait_mean",
            "emergency_wait_p95_mean",
            "emergency_wait_p99_mean",
            "normal_vehicle_avg_wait_mean",
            "normal_vehicle_p95_wait_mean",
            "priority_activation_count_mean",
            "emergency_hold_count_mean",
            "emergency_total_hold_time_mean",
            "emergency_hold_max_time_mean",
            "emergency_hold_success_count_mean",
            "avg_wait_improvement_pct",
            "p95_wait_improvement_pct",
            "p99_wait_improvement_pct",
            "max_wait_improvement_pct",
            "throughput_change_pct",
            "queue_peak_change_pct",
            "stability_score",
        ])

        for key, summary in summaries.items():
            writer.writerow([
                key[0],
                key[1],
                key[2],
                key[3],
                summary["test_count"],
                summary["avg_wait_mean"],
                summary["avg_wait_std"],
                summary["median_wait_mean"],
                summary["max_wait_mean"],
                summary["wait_p50_mean"],
                summary["wait_p90_mean"],
                summary["wait_p95_mean"],
                summary["wait_p99_mean"],
                summary["queue_avg_mean"],
                summary["queue_peak_mean"],
                summary["total_crossed_mean"],
                summary["emergency_spawned_mean"],
                summary["emergency_crossed_mean"],
                summary["emergency_avg_wait_mean"],
                summary["emergency_max_wait_mean"],
                summary["emergency_wait_p95_mean"],
                summary["emergency_wait_p99_mean"],
                summary["normal_vehicle_avg_wait_mean"],
                summary["normal_vehicle_p95_wait_mean"],
                summary["priority_activation_count_mean"],
                summary["emergency_hold_count_mean"],
                summary["emergency_total_hold_time_mean"],
                summary["emergency_hold_max_time_mean"],
                summary["emergency_hold_success_count_mean"],
                summary.get("avg_wait_improvement_pct", 0.0),
                summary.get("p95_wait_improvement_pct", 0.0),
                summary.get("p99_wait_improvement_pct", 0.0),
                summary.get("max_wait_improvement_pct", 0.0),
                summary.get("throughput_change_pct", 0.0),
                summary.get("queue_peak_change_pct", 0.0),
                summary.get("stability_score", 0.0),
            ])

    return path


def plot_metric_by_group(summaries, metric, title, ylabel, output_path):
    if not summaries:
        return

    labels = []
    values = []

    for key, summary in summaries.items():
        scenario_id, mode, controller_version, provider = key
        label = f"{scenario_id}\n{mode}\n{controller_version}\n{provider}"
        labels.append(label)
        values.append(summary.get(metric, 0))

    plt.figure(figsize=(max(14, len(labels) * 0.9), 7))
    plt.bar(labels, values)
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xticks(rotation=75, ha="right")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def write_markdown_report(summaries, output_dir, batch_run_id=None):
    path = output_dir / "batch_report.md"

    lines = []
    lines.append("# Traffic Simulation Batch Report\n")
    lines.append(f"Generated at: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n")

    if batch_run_id:
        lines.append(f"Batch Run ID: `{batch_run_id}`\n")

    lines.append("## Summary by Scenario / Controller / Provider\n")

    lines.append(
        "| Scenario | Mode | Controller | Provider | Tests | Avg Wait | Std | Median Wait | Max Wait | P50 | P90 | P95 | P99 | Queue Avg | Queue Peak | Crossed | Emg Spawned | Emg Crossed | Emg Avg Wait | Emg Max Wait | Emg P95 | Emg P99 | Normal Avg Wait | Normal P95 | Priority Count | Hold Count | Hold Total | Hold Max | Hold Success | Avg Improve % | P95 Improve % | P99 Improve % | Max Improve % | Throughput Change % | Queue Peak Change % |"
    )
    lines.append(
        "|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    )

    for key, s in summaries.items():
        lines.append(
            f"| {key[0]} | {key[1]} | {key[2]} | {key[3]} | "
            f"{s['test_count']} | {s['avg_wait_mean']} | {s['avg_wait_std']} | "
            f"{s['median_wait_mean']} | {s['max_wait_mean']} | "
            f"{s['wait_p50_mean']} | {s['wait_p90_mean']} | "
            f"{s['wait_p95_mean']} | {s['wait_p99_mean']} | "
            f"{s['queue_avg_mean']} | {s['queue_peak_mean']} | "
            f"{s['total_crossed_mean']} | "
            f"{s['emergency_spawned_mean']} | "
            f"{s['emergency_crossed_mean']} | "
            f"{s['emergency_avg_wait_mean']} | "
            f"{s['emergency_max_wait_mean']} | "
            f"{s['emergency_wait_p95_mean']} | "
            f"{s['emergency_wait_p99_mean']} | "
            f"{s['normal_vehicle_avg_wait_mean']} | "
            f"{s['normal_vehicle_p95_wait_mean']} | "
            f"{s['priority_activation_count_mean']} | "
            f"{s['emergency_hold_count_mean']} | "
            f"{s['emergency_total_hold_time_mean']} | "
            f"{s['emergency_hold_max_time_mean']} | "
            f"{s['emergency_hold_success_count_mean']} | "
            f"{s.get('avg_wait_improvement_pct', 0.0)} | "
            f"{s.get('p95_wait_improvement_pct', 0.0)} | "
            f"{s.get('p99_wait_improvement_pct', 0.0)} | "
            f"{s.get('max_wait_improvement_pct', 0.0)} | "
            f"{s.get('throughput_change_pct', 0.0)} | "
            f"{s.get('queue_peak_change_pct', 0.0)} |"
        )

    lines.append("\n## Generated Files\n")
    lines.append("- `raw_results.csv`")
    lines.append("- `summary_by_group.csv`")
    lines.append("- `avg_wait_by_group.png`")
    lines.append("- `max_wait_by_group.png`")
    lines.append("- `wait_p90_by_group.png`")
    lines.append("- `wait_p95_by_group.png`")
    lines.append("- `wait_p99_by_group.png`")
    lines.append("- `queue_avg_by_group.png`")
    lines.append("- `queue_peak_by_group.png`")
    lines.append("- `throughput_by_group.png`")
    lines.append("- `emergency_avg_wait_by_group.png`")
    lines.append("- `emergency_max_wait_by_group.png`")
    lines.append("- `emergency_p95_wait_by_group.png`")
    lines.append("- `emergency_p99_wait_by_group.png`")
    lines.append("- `priority_activation_count_by_group.png`")
    lines.append("- `emergency_hold_count_by_group.png`")
    lines.append("- `emergency_total_hold_time_by_group.png`")
    lines.append("- `emergency_hold_success_count_by_group.png`")
    lines.append("- `avg_wait_improvement_by_group.png`")
    lines.append("- `p95_wait_improvement_by_group.png`")
    lines.append("- `p99_wait_improvement_by_group.png`")
    lines.append("- `max_wait_improvement_by_group.png`")
    lines.append("- `throughput_change_by_group.png`")
    lines.append("- `queue_peak_change_by_group.png`")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return path


def generate_report(batch_run_id=None):
    output_dir = build_output_dir(batch_run_id=batch_run_id)
    results = load_results(batch_run_id=batch_run_id)

    grouped = defaultdict(list)

    for result in results:
        grouped[get_group_key(result)].append(result)

    summaries = {
        key: summarize_group(items)
        for key, items in grouped.items()
    }

    add_fixed_comparison_metrics(summaries)

    write_raw_csv(results, output_dir)
    write_summary_csv(summaries, output_dir)
    write_markdown_report(summaries, output_dir, batch_run_id=batch_run_id)

    plot_metric_by_group(
        summaries,
        "avg_wait_mean",
        "Average Wait by Test Group",
        "Average Wait (sec)",
        output_dir / "avg_wait_by_group.png",
    )

    plot_metric_by_group(
        summaries,
        "max_wait_mean",
        "Maximum Wait by Test Group",
        "Max Wait (sec)",
        output_dir / "max_wait_by_group.png",
    )

    plot_metric_by_group(
        summaries,
        "wait_p90_mean",
        "P90 Wait by Test Group",
        "P90 Wait (sec)",
        output_dir / "wait_p90_by_group.png",
    )

    plot_metric_by_group(
        summaries,
        "wait_p95_mean",
        "P95 Wait by Test Group",
        "P95 Wait (sec)",
        output_dir / "wait_p95_by_group.png",
    )

    plot_metric_by_group(
        summaries,
        "wait_p99_mean",
        "P99 Wait by Test Group",
        "P99 Wait (sec)",
        output_dir / "wait_p99_by_group.png",
    )

    plot_metric_by_group(
        summaries,
        "queue_avg_mean",
        "Average Queue Length by Test Group",
        "Average Queue Length",
        output_dir / "queue_avg_by_group.png",
    )

    plot_metric_by_group(
        summaries,
        "queue_peak_mean",
        "Queue Peak by Test Group",
        "Queue Peak",
        output_dir / "queue_peak_by_group.png",
    )

    plot_metric_by_group(
        summaries,
        "total_crossed_mean",
        "Throughput by Test Group",
        "Average Total Crossed",
        output_dir / "throughput_by_group.png",
    )

    plot_metric_by_group(
        summaries,
        "emergency_avg_wait_mean",
        "Emergency Average Wait by Test Group",
        "Emergency Avg Wait (sec)",
        output_dir / "emergency_avg_wait_by_group.png",
    )

    plot_metric_by_group(
        summaries,
        "emergency_max_wait_mean",
        "Emergency Max Wait by Test Group",
        "Emergency Max Wait (sec)",
        output_dir / "emergency_max_wait_by_group.png",
    )

    plot_metric_by_group(
        summaries,
        "emergency_wait_p95_mean",
        "Emergency P95 Wait by Test Group",
        "Emergency P95 Wait (sec)",
        output_dir / "emergency_p95_wait_by_group.png",
    )

    plot_metric_by_group(
        summaries,
        "emergency_wait_p99_mean",
        "Emergency P99 Wait by Test Group",
        "Emergency P99 Wait (sec)",
        output_dir / "emergency_p99_wait_by_group.png",
    )

    plot_metric_by_group(
        summaries,
        "priority_activation_count_mean",
        "Priority Activation Count by Test Group",
        "Average Priority Activations",
        output_dir / "priority_activation_count_by_group.png",
    )

    plot_metric_by_group(
        summaries,
        "emergency_hold_count_mean",
        "Emergency Hold Count by Test Group",
        "Average Hold Count",
        output_dir / "emergency_hold_count_by_group.png",
    )

    plot_metric_by_group(
        summaries,
        "emergency_total_hold_time_mean",
        "Emergency Total Hold Time by Test Group",
        "Hold Time (sec)",
        output_dir / "emergency_total_hold_time_by_group.png",
    )

    plot_metric_by_group(
        summaries,
        "emergency_hold_success_count_mean",
        "Emergency Hold Success Count by Test Group",
        "Hold Success Count",
        output_dir / "emergency_hold_success_count_by_group.png",
    )

    plot_metric_by_group(
        summaries,
        "avg_wait_improvement_pct",
        "Average Wait Improvement vs Fixed Baseline",
        "Improvement (%)",
        output_dir / "avg_wait_improvement_by_group.png",
    )

    plot_metric_by_group(
        summaries,
        "p95_wait_improvement_pct",
        "P95 Wait Improvement vs Fixed Baseline",
        "Improvement (%)",
        output_dir / "p95_wait_improvement_by_group.png",
    )

    plot_metric_by_group(
        summaries,
        "p99_wait_improvement_pct",
        "P99 Wait Improvement vs Fixed Baseline",
        "Improvement (%)",
        output_dir / "p99_wait_improvement_by_group.png",
    )

    plot_metric_by_group(
        summaries,
        "max_wait_improvement_pct",
        "Max Wait Improvement vs Fixed Baseline",
        "Improvement (%)",
        output_dir / "max_wait_improvement_by_group.png",
    )

    plot_metric_by_group(
        summaries,
        "throughput_change_pct",
        "Throughput Change vs Fixed Baseline",
        "Change (%)",
        output_dir / "throughput_change_by_group.png",
    )

    plot_metric_by_group(
        summaries,
        "queue_peak_change_pct",
        "Queue Peak Change vs Fixed Baseline",
        "Change (%)",
        output_dir / "queue_peak_change_by_group.png",
    )

    print(f"[REPORT] Generated in: {output_dir}")
    return output_dir


if __name__ == "__main__":
    generate_report()