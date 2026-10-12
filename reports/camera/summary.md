# Sabit süre, tam bilgili adaptif ve kameralı adaptif

Ortalama bekleme süresi (sn), ölçüme giren tüm araçlar. Üç kontrolcü aynı senaryo ve tohumlarla koşuldu.
Kameralı kontrolcü v3 ile aynı karar kuralını kullanır, girdisi yalnızca YOLO tespitleridir.

- Kameralı kontrolün en iyi sabit süreye göre kazancı: ortanca %26, ortalama %32, en düşük %-4
- Kameralı kontrolün ortalamada sabit sürenin önünde olduğu senaryo: 20/22
- Tam bilgiye göre kayıp (kamera eksi v3): ortanca +1.2 sn, en yüksek +5.6 sn

| Senaryo | en iyi sabit | tam bilgi (v3) | kamera | kamera kazancı (en iyi sabit) | kameranın v3'e göre kaybı | kamera önde (koşu) | geçemeyen: v3 / kamera |
|---|---:|---:|---:|---:|---:|---:|---:|
| balanced_traffic | 23.9 (6s) | 21.7 | 23.0 | %4 | +1.3 sn | 7/10 | %7 / %6 |
| right_heavy_traffic | 59.3 (6s) | 27.9 | 32.5 | %45 | +4.6 sn | 10/10 | %9 / %12 |
| vertical_heavy_traffic | 42.5 (6s) | 20.4 | 20.0 | %53 | -0.4 sn | 10/10 | %7 / %7 |
| peak_traffic | 48.7 (6s) | 52.5 | 49.4 | %-1 | -3.2 sn | 6/10 | %19 / %18 |
| low_traffic | 17.4 (6s) | 9.4 | 12.9 | %26 | +3.5 sn | 10/10 | %4 / %4 |
| turn_heavy_traffic | 24.5 (6s) | 22.4 | 24.4 | %0 | +2.0 sn | 5/10 | %7 / %7 |
| single_direction_traffic | 162.5 (5s) | 0.0 | 0.0 | %100 | +0.0 sn | 10/10 | %2 / %2 |
| extreme_directional_traffic | 121.0 (5s) | 7.0 | 7.2 | %94 | +0.2 sn | 10/10 | %3 / %4 |
| sparse_traffic | 16.3 (6s) | 3.9 | 5.3 | %68 | +1.4 sn | 10/10 | %0 / %1 |
| idle_intersection | 14.4 (6s) | 4.3 | 5.9 | %59 | +1.6 sn | 10/10 | %0 / %1 |
| direction_shift_traffic | 24.6 (6s) | 21.9 | 22.4 | %9 | +0.5 sn | 7/10 | %7 / %7 |
| demand_shift_traffic | 24.7 (6s) | 22.5 | 24.0 | %3 | +1.6 sn | 5/10 | %6 / %7 |
| burst_traffic | 28.7 (6s) | 27.6 | 27.9 | %3 | +0.3 sn | 7/10 | %9 / %8 |
| alternating_heavy_traffic | 29.0 (6s) | 28.8 | 28.4 | %2 | -0.3 sn | 7/10 | %9 / %9 |
| asymmetric_peak_traffic | 92.3 (5s) | 67.7 | 68.9 | %25 | +1.2 sn | 10/10 | %31 / %31 |
| turning_conflict_traffic | 57.7 (6s) | 34.7 | 32.4 | %44 | -2.3 sn | 10/10 | %12 / %11 |
| emergency_balanced_traffic | 23.5 (6s) | 22.6 | 22.6 | %4 | -0.1 sn | 6/10 | %7 / %8 |
| emergency_right_heavy_traffic | 55.1 (5s) | 24.5 | 28.4 | %48 | +4.0 sn | 10/10 | %10 / %11 |
| emergency_peak_traffic | 51.0 (6s) | 55.1 | 52.9 | %-4 | -2.2 sn | 3/10 | %20 / %20 |
| emergency_sparse_traffic | 16.1 (6s) | 3.9 | 5.2 | %68 | +1.3 sn | 10/10 | %1 / %1 |
| emergency_low_frequency_mixed_traffic | 19.8 (6s) | 14.8 | 17.3 | %12 | +2.6 sn | 8/10 | %5 / %5 |
| mixed_master_scenario | 49.3 (6s) | 27.4 | 33.0 | %33 | +5.6 sn | 3/3 | %1 / %2 |

## Acil durum araçlarının ortalama beklemesi (sn)

| Senaryo | en iyi sabit | tam bilgi (v3) | kamera |
|---|---:|---:|---:|
| emergency_balanced_traffic | 27.7 | 3.4 | 9.0 |
| emergency_right_heavy_traffic | 46.7 | 3.0 | 11.1 |
| emergency_peak_traffic | 43.9 | 9.6 | 35.0 |
| emergency_sparse_traffic | 12.7 | 0.6 | 1.3 |
| emergency_low_frequency_mixed_traffic | 14.7 | 1.6 | 2.2 |
| mixed_master_scenario | 43.1 | 3.1 | 17.4 |
