from statistics import median


def summarize_direction(waits, queue_samples, queue_peak):
    avg_wait = sum(waits) / len(waits) if waits else 0.0
    med_wait = median(waits) if waits else 0.0
    max_wait = max(waits) if waits else 0.0
    q_avg = sum(queue_samples) / len(queue_samples) if queue_samples else 0.0
    return {
        "avg_wait": round(avg_wait, 3),
        "median_wait": round(med_wait, 3),
        "max_wait": round(max_wait, 3),
        "crossed": len(waits),
        "queue_length_average": round(q_avg, 3),
        "queue_length_peak": int(queue_peak),
    }
