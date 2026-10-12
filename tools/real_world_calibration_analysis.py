"""Parses data/real_world_calibration.csv (manual green-phase annotations from
real intersection recordings) and derives per-phase / per-direction discharge
rate and start-up lost time statistics for calibrating the simulation against
real traffic (see docs/scenario_capacity_calibration.md).

Run directly: python tools/real_world_calibration_analysis.py
"""

import csv
import re
import statistics
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "real_world_calibration.csv"

TIME_RE = re.compile(
    r"^(?:(\d+)\s*(?:dk|dkı|fk)\s*)?(?:(\d+(?:\.\d+)?)\s*sn)?$"
)


def parse_time(raw):
    s = raw.strip()
    if not s:
        return None
    m = TIME_RE.match(s)
    if m and (m.group(1) or m.group(2)):
        minutes = int(m.group(1)) if m.group(1) else 0
        seconds = float(m.group(2)) if m.group(2) else 0.0
        return minutes * 60 + seconds
    return float(s)


def load_rows():
    rows = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            if not raw.get("kavsak"):
                continue
            start = parse_time(raw["yesil_baslangic_sn"])
            first = parse_time(raw["ilk_arac_gecis_sn"])
            end = parse_time(raw["yesil_bitis_sn"])
            count = int(raw["bosalan_arac_sayisi"])
            note = (raw.get("not") or "").strip()
            lanes = int(raw["serit sayısı"])
            discharge_rate = count / (end - start)
            rows.append({
                "video": raw["video_dosyasi"],
                "kavsak": raw["kavsak"],
                "yon": raw["yon"],
                "faz_no": raw["faz_no"],
                "start": start,
                "first": first,
                "end": end,
                "count": count,
                "note": note,
                "lanes": lanes,
                "duration": end - start,
                "lost_time": first - start,
                "discharge_rate": discharge_rate,
                "discharge_rate_per_lane": discharge_rate / lanes,
            })
    return rows


def fmt(x):
    return f"{x:.3f}"


def main():
    rows = load_rows()

    print(f"{'video':<16}{'kavsak':<10}{'yon':<8}{'faz':<4}{'sure':>7}{'lost':>7}{'adet':>6}{'serit':>6}{'oran(a/s)':>11}{'oran/serit':>12}  not")
    for r in rows:
        flag = " <-- NOT VAR" if r["note"] else ""
        print(f"{r['video']:<16}{r['kavsak']:<10}{r['yon']:<8}{r['faz_no']:<4}"
              f"{fmt(r['duration']):>7}{fmt(r['lost_time']):>7}{r['count']:>6}{r['lanes']:>6}"
              f"{fmt(r['discharge_rate']):>11}{fmt(r['discharge_rate_per_lane']):>12}{flag}")

    print("\n--- kavsak+yon bazinda ozet ---")
    groups = {}
    for r in rows:
        key = (r["kavsak"], r["yon"])
        groups.setdefault(key, []).append(r)

    for key, group_rows in sorted(groups.items()):
        rates = [r["discharge_rate"] for r in group_rows]
        per_lane = [r["discharge_rate_per_lane"] for r in group_rows]
        lost = [r["lost_time"] for r in group_rows]
        lanes = group_rows[0]["lanes"]
        print(f"{key[0]:<10}{key[1]:<8} n={len(group_rows):<3} serit={lanes} "
              f"discharge_rate ort={statistics.mean(rates):.3f} veh/s  "
              f"serit-basi ort={statistics.mean(per_lane):.3f} veh/s/serit "
              f"(min={min(per_lane):.3f}, max={max(per_lane):.3f})  "
              f"lost_time ort={statistics.mean(lost):.2f}s")

    all_rates = [r["discharge_rate"] for r in rows]
    all_per_lane = [r["discharge_rate_per_lane"] for r in rows]
    all_lost = [r["lost_time"] for r in rows]
    print(f"\nTUM VERI  n={len(rows)}  discharge_rate ort={statistics.mean(all_rates):.3f} veh/s "
          f"(median={statistics.median(all_rates):.3f}, min={min(all_rates):.3f}, max={max(all_rates):.3f})")
    print(f"          serit-basi ort={statistics.mean(all_per_lane):.3f} veh/s/serit "
          f"(median={statistics.median(all_per_lane):.3f}, min={min(all_per_lane):.3f}, max={max(all_per_lane):.3f})")
    print(f"          lost_time ort={statistics.mean(all_lost):.2f}s "
          f"(median={statistics.median(all_lost):.2f}, min={min(all_lost):.2f}, max={max(all_lost):.2f})")

    print("\n--- notlu (dikkat gerektiren) satirlar ---")
    for r in rows:
        if r["note"]:
            print(f"- {r['video']} / {r['kavsak']} / {r['yon']} faz {r['faz_no']}: {r['note']}")

    print("\n--- olasi veri sorunlari ---")
    seen = {}
    for r in rows:
        key = (r["video"], r["kavsak"], r["yon"], r["faz_no"])
        if key in seen:
            print(f"- YINELENEN faz_no: {r['video']} / {r['kavsak']} / {r['yon']} faz {r['faz_no']} "
                  f"iki kez var (t={seen[key]['start']}s ve t={r['start']}s) -- muhtemelen ikincisi faz "
                  f"{int(r['faz_no'])+1} olmali")
        seen[key] = r


if __name__ == "__main__":
    main()
