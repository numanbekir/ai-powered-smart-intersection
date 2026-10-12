import json
from datetime import datetime

from core.paths import DATA_DIR


class ResultRegistry:
    def __init__(self):
        self.index_file = DATA_DIR / "results_index.json"
        self.batches_dir = DATA_DIR / "batches"

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.batches_dir.mkdir(parents=True, exist_ok=True)

        if not self.index_file.exists():
            self._write_index([])

    def _read_index(self):
        if not self.index_file.exists():
            return []

        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            return data if isinstance(data, list) else []

        except Exception:
            return []

    def _write_index(self, data):
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _get_batch_run_id(self, result):
        return (
            result.get("batch_identity", {}).get("batch_run_id")
            or "manual_runs"
        )

    def _get_batch_file(self, batch_run_id):
        return self.batches_dir / f"{batch_run_id}.jsonl"

    def _iter_jsonl_file(self, batch_file, include_interrupted=True):
        if not batch_file.exists():
            return

        with open(batch_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if not line:
                    continue

                try:
                    result = json.loads(line)
                except Exception:
                    continue

                if not include_interrupted and result.get("interrupted", False):
                    continue

                yield result

    def _build_index_row(self, result, batch_file):
        exp = result.get("experiment_identity", {})
        test = result.get("test_identity", {})
        metrics = result.get("metrics", {})
        batch = result.get("batch_identity", {})

        return {
            "batch_run_id": batch.get("batch_run_id", "manual_runs"),
            "stored_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "batch_file": str(batch_file.relative_to(DATA_DIR)),

            "timestamp": result.get("timestamp"),
            "test_name": test.get("test_name"),
            "scenario_id": exp.get("scenario_id"),
            "scenario_name": test.get("scenario_name"),
            "seed": test.get("seed"),

            "controller_mode": exp.get("controller_mode"),
            "controller_version_id": exp.get(
                "controller_version_id",
                "fixed_baseline",
            ),
            "state_provider_id": exp.get("state_provider_id"),

            "overall_avg_wait": metrics.get("overall_avg_wait", 0),
            "overall_median_wait": metrics.get("overall_median_wait", 0),
            "overall_max_wait": metrics.get("overall_max_wait", 0),
            "overall_wait_p50": metrics.get("overall_wait_p50", 0),
            "overall_wait_p90": metrics.get("overall_wait_p90", 0),
            "overall_wait_p95": metrics.get("overall_wait_p95", 0),
            "overall_wait_p99": metrics.get("overall_wait_p99", 0),

            "queue_length_average": metrics.get("queue_length_average", 0),
            "queue_length_peak": metrics.get("queue_length_peak", 0),
            "total_crossed": metrics.get("total_crossed", 0),
            "interrupted": result.get("interrupted", False),
        }

    def add(self, result):
        batch_run_id = self._get_batch_run_id(result)
        batch_file = self._get_batch_file(batch_run_id)

        with open(batch_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

        index = self._read_index()
        index.append(self._build_index_row(result, batch_file))
        self._write_index(index)

    def all(self, include_interrupted=True):
        index = self._read_index()
        results = []

        batch_files = sorted({
            row.get("batch_file")
            for row in index
            if row.get("batch_file")
        })

        for relative_path in batch_files:
            batch_file = DATA_DIR / relative_path

            for result in self._iter_jsonl_file(
                batch_file,
                include_interrupted=include_interrupted,
            ):
                results.append(result)

        return results

    def list_all(self):
        return self.all(include_interrupted=True)

    def completed(self):
        return self.all(include_interrupted=False)

    def by_batch(self, batch_run_id, include_interrupted=False):
        batch_file = self._get_batch_file(batch_run_id)

        return list(
            self._iter_jsonl_file(
                batch_file,
                include_interrupted=include_interrupted,
            )
        )

    def clear(self):
        self._write_index([])

        if self.batches_dir.exists():
            for file in self.batches_dir.glob("*.jsonl"):
                file.unlink()