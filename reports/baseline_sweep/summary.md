# Sabit süre taraması ve adaptif karşılaştırma

Ortalama bekleme süresi (sn), koşu ortalaması. Ölçüme giren tüm araçları kapsar: kavşağı geçenlerin beklemesi ve koşu bittiğinde hâlâ kuyrukta olanların o ana kadarki beklemesi. Kazanç, bekleme süresindeki azalmadır.

- Senaryo sayısı: 22
- Varsayılan sabit süreye (10s) göre kazanç: ortalama %50, en düşük %5
- Her senaryonun en iyi sabit süresine göre kazanç: ortanca %43, ortalama %37, en düşük %-8
- Adaptifin ortalamada önde olduğu senaryo: 20/22
- Adaptifin koşuların en az %80'inde önde olduğu senaryo: 16/22
- Tek bir sabit süre seçilseydi (senaryo başına varsayılana oranın ortalaması, küçük olan iyi): 5s=0.923, 6s=0.827, 8s=1.046, 10s=1.000, 12s=1.017

| Senaryo | sabit 5s | sabit 6s | sabit 8s | sabit 10s | sabit 12s | en iyi sabit | en iyi adaptif | kazanç (sabit 10s) | kazanç (en iyi sabit) | adaptif önde (koşu) | geçemeyen: sabit / adaptif |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| balanced_traffic | 28.8 | 23.9 | 31.9 | 33.1 | 30.3 | 6s | 21.7 (v3) | %34 | %9 | 7/10 | %7 / %7 |
| right_heavy_traffic | 60.8 | 59.3 | 72.0 | 65.2 | 66.7 | 6s | 27.9 (v3) | %57 | %53 | 10/10 | %23 / %9 |
| vertical_heavy_traffic | 46.7 | 42.5 | 57.5 | 49.7 | 53.5 | 6s | 20.4 (v3) | %59 | %52 | 10/10 | %17 / %7 |
| peak_traffic | 52.5 | 48.7 | 67.8 | 57.8 | 61.1 | 6s | 52.5 (v3) | %9 | %-8 | 1/10 | %18 / %19 |
| low_traffic | 22.0 | 17.4 | 20.4 | 24.3 | 21.2 | 6s | 9.4 (v3) | %61 | %46 | 10/10 | %5 / %4 |
| turn_heavy_traffic | 29.4 | 24.5 | 32.6 | 33.8 | 30.4 | 6s | 22.4 (v3) | %34 | %8 | 8/10 | %8 / %7 |
| single_direction_traffic | 162.5 | 166.5 | 179.9 | 167.7 | 169.3 | 5s | 0.0 (v3) | %100 | %100 | 10/10 | %82 / %2 |
| extreme_directional_traffic | 121.0 | 126.9 | 139.8 | 128.7 | 131.8 | 5s | 7.0 (v3) | %95 | %94 | 10/10 | %57 / %3 |
| sparse_traffic | 20.1 | 16.3 | 19.1 | 21.2 | 22.0 | 6s | 3.9 (v3) | %82 | %76 | 10/10 | %5 / %0 |
| idle_intersection | 16.0 | 14.4 | 16.2 | 14.6 | 21.9 | 6s | 4.3 (v3) | %71 | %70 | 10/10 | %3 / %0 |
| direction_shift_traffic | 29.9 | 24.6 | 32.6 | 33.7 | 31.0 | 6s | 21.9 (v3) | %35 | %11 | 8/10 | %7 / %7 |
| demand_shift_traffic | 29.9 | 24.7 | 32.7 | 34.1 | 31.4 | 6s | 22.5 (v3) | %34 | %9 | 8/10 | %7 / %6 |
| burst_traffic | 34.8 | 28.7 | 39.1 | 37.8 | 36.7 | 6s | 27.6 (v3) | %27 | %4 | 5/10 | %8 / %9 |
| alternating_heavy_traffic | 34.6 | 29.0 | 39.6 | 37.5 | 35.8 | 6s | 28.8 (v3) | %23 | %1 | 5/10 | %9 / %9 |
| asymmetric_peak_traffic | 92.3 | 94.9 | 111.1 | 98.7 | 102.4 | 5s | 53.7 (RH-v1) | %46 | %42 | 10/10 | %40 / %23 |
| turning_conflict_traffic | 59.6 | 57.7 | 77.6 | 64.5 | 70.0 | 6s | 31.5 (RH-v1) | %51 | %45 | 10/10 | %22 / %10 |
| emergency_balanced_traffic | 29.6 | 23.5 | 30.1 | 32.2 | 29.9 | 6s | 22.6 (v3) | %30 | %4 | 6/10 | %7 / %7 |
| emergency_right_heavy_traffic | 55.1 | 56.0 | 66.7 | 59.6 | 60.9 | 5s | 24.2 (RH-v1) | %59 | %56 | 10/10 | %23 / %9 |
| emergency_peak_traffic | 52.9 | 51.0 | 66.9 | 58.2 | 59.4 | 6s | 55.1 (v3) | %5 | %-8 | 4/10 | %19 / %20 |
| emergency_sparse_traffic | 18.0 | 16.1 | 18.6 | 21.1 | 22.2 | 6s | 3.9 (v3) | %81 | %76 | 10/10 | %5 / %1 |
| emergency_low_frequency_mixed_traffic | 25.2 | 19.8 | 25.3 | 28.5 | 26.4 | 6s | 14.8 (v3) | %48 | %25 | 8/10 | %6 / %5 |
| mixed_master_scenario | 56.3 | 49.3 | 77.9 | 59.0 | 66.1 | 6s | 27.4 (v3) | %54 | %44 | 3/3 | %2 / %1 |
