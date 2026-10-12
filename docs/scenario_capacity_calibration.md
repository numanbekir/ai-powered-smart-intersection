# Senaryo Talep Kalibrasyonu: Gerçekçi v/c Oranları

> **2026-07-24 güncellemesi:** Bu dokümandaki ~1.116 araç/sn kapasite artık
> **gerçek kavşak kayıtlarıyla kalibre edilmiş değil** — motorun kendi
> sabit-hız/mesafe fiziğinden ölçülmüştü. 2026-07-24'te gerçek kayıtlarla
> (bkz. dosya sonundaki "2026-07-24: Gerçek Dünya Kalibrasyonu" bölümü)
> karşılaştırılınca motorun ~2.3x fazla iyimser olduğu bulundu ve
> düzeltildi. Bu dosyanın üst kısmındaki v/c hedefleri (0.15-0.90) hâlâ
> geçerli/kullanılan referans niyetleridir, ama onları üreten
> `spawn_interval` sayıları ve bu sayfadaki mutlak `avg_wait` rakamları artık
> **yeni (düşük) kapasiteye göre yeniden ölçeklenmiş** durumda — güncel
> sayılar için dosya sonuna bakın.

## Bulgu: senaryolar hiç ölçülmeden ayarlanmıştı

Kullanıcı, `mixed_master_scenario`'da adaptive stratejilerin fixed'ten kötü çıkmasının araç üretim mekanizmasındaki bir dengesizlikten kaynaklanıp kaynaklanmadığını sordu. İnceleme şunu ortaya çıkardı: **20 senaryonun `spawn_interval` değerleri hiçbir kapasite ölçümüne dayanmadan ayarlanmıştı.** Kullanıcı bunu doğruladı: "kasıtlı bir durum değil."

`generateVehicles()` tek bir spawner thread'i, her `spawn_interval` simüle saniyede 1 araç üretiyor (yön, `direction_density` ağırlıklarıyla seçiliyor — density mutlak üretim hızını değil, yalnızca yönler arası oranı belirliyor). Bu mekanizmanın kendisi doğru; sorun sadece `spawn_interval` değerlerinin hangi trafik yoğunluğunu temsil ettiğinin hiç doğrulanmamış olmasıydı.

## Ölçülen kapasite

Doygun (sınırsız talep, sürekli yeşil) sistem throughput'u ampirik olarak ölçüldü (`balanced_traffic` tabanlı, `spawn_interval=0.3`, 600s, 3 seed):

| Seed | crossed | rate (araç/sn) |
|---|---:|---:|
| 42 | 665 | 1.108 |
| 101 | 678 | 1.130 |
| 202 | 665 | 1.108 |
| **Ortalama** | | **1.116 araç/sn** |

Bu, projenin önceki dokümante edilmiş tahminiyle ("~1.16 araç/sn") uyumlu (%4 fark) — bağımsız ölçüm, mevcut tavanı doğruluyor.

## Eski durum: neredeyse tüm senaryolar zaten "peak" seviyesindeydi

20 senaryonun mevcut `spawn_interval`'ı bu kapasiteye karşı kontrol edildi:

| Durum | Senaryo sayısı | v/c aralığı |
|---|---|---|
| Kapasite üstü (>1.0) | 3 (`peak_traffic`, `asymmetric_peak_traffic`, `emergency_peak_traffic`) | 1.28-1.38 |
| Fiilen zaten "peak" (~0.90-1.0) | 14 | 0.90-1.0 |
| Hafif | 3 (`low_traffic`, `sparse_traffic`, `emergency_sparse_traffic`) | 0.36-0.50 |

Yani sorun yalnızca 3 "peak" isimli senaryo değildi — **`balanced_traffic`, `right_heavy_traffic`, `burst_traffic` gibi "orta/dengeli" isimli senaryoların büyük çoğunluğu da zaten kapasitenin ~%90'ında çalışıyordu.** Trafik yelpazesinde gerçek bir "orta yoğunluk" kategorisi yoktu — set neredeyse iki uca (boş/hafif ya da peak) sıkışmıştı.

## Yeni kalibrasyon: isim/niyete göre yayılmış v/c hedefleri

| v/c hedefi | Senaryolar |
|---|---|
| 0.15 | `idle_intersection` |
| 0.20 | `sparse_traffic`, `emergency_sparse_traffic` |
| 0.35 | `low_traffic` |
| 0.45 | `emergency_low_frequency_mixed_traffic` |
| 0.55 | `balanced_traffic`, `emergency_balanced_traffic`, `right_heavy_traffic`, `vertical_heavy_traffic`, `emergency_right_heavy_traffic`, `turn_heavy_traffic`, `direction_shift_traffic`, `extreme_directional_traffic` |
| 0.65 | `turning_conflict_traffic`, `alternating_heavy_traffic`, `single_direction_traffic`, `burst_traffic` |
| 0.90 | `peak_traffic`, `asymmetric_peak_traffic`, `emergency_peak_traffic` |

### Tam eski → yeni tablo

| Senaryo | Eski `spawn_interval` | Eski v/c | Yeni `spawn_interval` | Yeni v/c |
|---|---:|---:|---:|---:|
| idle_intersection | 1.00 | 0.90 | 5.97 | 0.15 |
| sparse_traffic | 2.50 | 0.36 | 4.48 | 0.20 |
| emergency_sparse_traffic | 2.50 | 0.36 | 4.48 | 0.20 |
| low_traffic | 1.80 | 0.50 | 2.56 | 0.35 |
| emergency_low_frequency_mixed_traffic | 1.00 | 0.90 | 1.99 | 0.45 |
| balanced_traffic | 1.00 | 0.90 | 1.63 | 0.55 |
| emergency_balanced_traffic | 1.00 | 0.90 | 1.63 | 0.55 |
| right_heavy_traffic | 1.00 | 0.90 | 1.63 | 0.55 |
| vertical_heavy_traffic | 1.00 | 0.90 | 1.63 | 0.55 |
| emergency_right_heavy_traffic | 1.00 | 0.90 | 1.63 | 0.55 |
| turn_heavy_traffic | 1.00 | 0.90 | 1.63 | 0.55 |
| direction_shift_traffic | 1.00 | 0.90 | 1.63 | 0.55 |
| extreme_directional_traffic | 1.00 | 0.90 | 1.63 | 0.55 |
| turning_conflict_traffic | 0.90 | 1.00 | 1.38 | 0.65 |
| alternating_heavy_traffic | 1.00 | 0.90 | 1.38 | 0.65 |
| single_direction_traffic | 1.00 | 0.90 | 1.38 | 0.65 |
| burst_traffic | 1.00 | 0.90 | 1.38 | 0.65 |
| peak_traffic | 0.70 | 1.28 | 1.00 | 0.90 |
| asymmetric_peak_traffic | 0.65 | 1.38 | 1.00 | 0.90 |
| emergency_peak_traffic | 0.70 | 1.28 | 1.00 | 0.90 |

`mixed_master_scenario`'nun 20 alt-bloklu `dynamic_spawn_interval_schedule`'ı, her bloğun kaynak senaryosunun YENİ değeriyle yeniden üretildi (`data/scenarios.json`) — zaman-ağırlıklı ortalama talep %86'dan **%55**'e (v/c) düştü, en yoğun blok artık tam olarak kapasitede (v/c=0.90), hiçbir blok kapasiteyi aşmıyor.

`core/config_defaults.py`'nin `default_scenario_config()` fallback'i de 1.0 → 1.63 (v/c≈0.55) olarak güncellendi.

## Arşivleme (eski kalıntılar temizlendi)

Bu kalibrasyon öncesi üretilen TÜM batch/rapor verisi, artık geçersiz talep seviyelerine dayandığından, gelecekteki `tools/report_generator.py` çalıştırmalarının (varsayılan, `batch_run_id=None`) varolan yeni verilerle sessizce karışmaması için taşındı:
- `data/batches/*.jsonl` (ve kullanıcının kendi manuel GUI koşularını içeren `manual_runs.jsonl` dahil) → `data/archive/pre_capacity_recalibration_20260716/batches/`
- `data/results_index.json` → içeriği aynı klasöre kopyalandı, canlı dosya `[]` olarak sıfırlandı
- `reports/batch_20260714_180508_report_*`, `reports/batch_report_20260715_054505` → `reports/archive_pre_capacity_recalibration_20260716/`
- `data/scenarios.json`'ın kalibrasyon öncesi hâli → `data/archive/scenarios_pre_capacity_recalibration_20260716.json`

(Not: bu dörtlü, 2026-07-22'de projeden tamamen çıkarılıp `../traffic_sim_data_archive/`'a taşındı — repoyu şişirmemek için, `docs/archive/` ile aynı gerekçeyle. Yollar yukarıda o zamanki taşımayı olduğu gibi belgeliyor.)

Hiçbir şey silinmedi, yalnızca canlı/varsayılan yoldan çıkarıldı.

## Yeni kalibrasyonla doğrulama: temiz ve tutarlı bir sonuç

Fixed / `adaptive_optimal_ground_truth_v3` / `adaptive_rolling_horizon_ground_truth` karşılaştırması, 6 temsili senaryo üzerinde tekrar koşuldu (5 seed, mixed_master 3 seed):

| Senaryo | Fixed avg | v3 avg | RH avg | RH iyileşme |
|---|---:|---:|---:|---:|
| balanced_traffic | 17.27 | 13.49 | 11.29 | **-%35** |
| right_heavy_traffic | 21.75 | 13.40 | 9.26 | **-%57** |
| single_direction_traffic | 35.98 | 0.00 | 0.00 | **-%100** |
| asymmetric_peak_traffic | 21.19 | 15.16 | 13.00 | **-%39** |
| emergency_peak_traffic | 16.95 | 15.87 | 15.34 | -%9 |
| **mixed_master_scenario** | **23.15** | 31.86 | 35.30 | **+%52 (kötü)** |

### Bu, önceki (yanlış kalibre) sonuçlardan çok daha temiz bir hikaye

- **5/6 standart senaryoda adaptive'in üstünlüğü artık net ve güçlü** — özellikle `emergency_peak_traffic`'te önceki (kapasite-üstü) ölçümde neredeyse sıfırlanan/tersine dönen kazanım, artık gerçek kapasite altında (v/c=0.90, hâlâ yoğun ama imkansız değil) tekrar pozitif ve tutarlı (-%9).
- **`mixed_master_scenario`'daki adaptive zayıflığının gerçek sebebi değişti.** Eskiden bu, "sürekli aşırı-doygunluk" (v/c ortalama %86, bazı bloklar >%100) olarak açıklanıyordu. Şimdi ortalama talep sadece %55 v/c — çoğu blok hafif/orta yoğun, sadece 3 blok (90s'lik) v/c=0.90'da. Buna rağmen fixed hâlâ açık farkla kazanıyor. **Yeni, daha kesin açıklama:** `mixed_master_scenario`'nun asıl zorluğu doygunluk değil, **her 90 saniyede bir rejim değişmesi**. Adaptive stratejiler (`discharge_rate`, rolling-horizon'da ayrıca `arrival_rate`) EMA ile ÖĞRENİLEN parametrelere dayanıyor — rejim aniden değiştiğinde (ör. `low_traffic` bloğundan `peak_traffic` bloğuna geçiş) bu öğrenilmiş değerler bir süre YANLIŞ/ESKİ kalıyor, bu adaptasyon gecikmesi sırasında kararlar suboptimal oluyor. Fixed hiçbir şey öğrenmediğinden bu geçişten hiç etkilenmiyor. Bunu destekleyen kanıt: daha FAZLA öğrenilmiş parametreye sahip rolling-horizon (`discharge_rate` + `arrival_rate`), yalnızca `discharge_rate` öğrenen v3'ten bile kötü (35.30 vs 31.86) — öğrenilecek parametre arttıkça rejim-değişimi hassasiyeti artıyor.

Bu, önceki (artık projeden çıkarılmış) dokümanlardaki "doygunlukta sık faz değişimi" hipotezinin yerini alan, veriyle daha tutarlı bir açıklama.

## Sonuç

Kullanıcının sorusu doğru bir teşhisti: senaryolar gerçekten ölçülmeden ayarlanmıştı, ve bu bazı sonuçları (özellikle `emergency_peak_traffic` ve `mixed_master_scenario`) bozuyordu. Kalibrasyon sonrası tablo artık çok daha tutarlı ve yorumlanabilir: adaptive, gerçekçi talep altında hemen her standart senaryoda güçlü bir kazanım veriyor; `mixed_master_scenario`'daki tek zayıflık artık net bir mekanizmaya (öğrenilmiş-parametre rejim-değişimi gecikmesi) bağlanabiliyor — bu da gelecekte hedefli bir çözüm (ör. rejim değişimini algılayıp öğrenilmiş parametreleri hızla sıfırlayan/adapte eden bir mekanizma) için somut bir yön veriyor.

## Ek: `demand_shift_traffic` (rejim-değişimi izolasyon senaryosu)

Yukarıdaki "rejim-değişimi" hipotezini doğrudan test etmek için 21. bir kanonik senaryo eklendi. Mevcut rejim-değişimi senaryoları (`direction_shift_traffic`, `burst_traffic`, `alternating_heavy_traffic`) yalnızca **yön** dağılımını (`dynamic_density_schedule`) değiştiriyor, `spawn_interval` sabit kalıyor — yani talep **büyüklüğünün** tek başına değişip değişmediğini izole eden bir senaryo yoktu. `mixed_master_scenario`'daki rejim değişimi ise hem yön hem büyüklük aynı anda sıçradığı için, zayıflığın gerçek kaynağını (yön mü, büyüklük mü, yoksa ikisi birden mi) ayırt etmek zordu.

`demand_shift_traffic`, yön dağılımını sabit (dengeli, 25/25/25/25) tutup yalnızca `spawn_interval`'ı `dynamic_spawn_interval_schedule` ile 30s'de bir sparse (v/c≈0.20, `spawn_interval=4.48`) ↔ peak (v/c≈0.90, `spawn_interval=1.0`) arasında sıçratıyor (120s, 4 blok). `simulation/engine.py`'nin `get_current_direction_density()` ve `get_current_spawn_interval()` metotları birbirinden tamamen bağımsız çalıştığı için (`mixed_master_scenario` zaten ikisini birden kullanıyor), bu ayrım mevcut motor mekanizmasıyla doğrudan destekleniyor — motor tarafında değişiklik gerekmedi. Emergency kapalı tutuldu (mekanizma izolasyonu bozulmasın diye).

Beklenti: eğer `mixed_master_scenario`'daki zayıflığın asıl kaynağı öğrenilen `discharge_rate`/`arrival_rate`'in büyüklük sıçramalarında bayatlaması ise, bu davranış `demand_shift_traffic`'te de gözlenmeli (özellikle rolling-horizon'un v3'ten kötü çıkması paterni) — `direction_shift_traffic`'te bu derece belirgin olmamalı. Bu, sadece 6 senaryoluk spot-check yerine tam batch matrisiyle (bkz. proje `tools/run_batch_tests.py`) doğrulanacak.

### Sonuç: tam batch matrisiyle doğrulama (2026-07-16, 20 seed, `batch_20260716_115601`)

22 kanonik senaryo × 5 kontrolcü × 20 seed (mixed_master 3 seed) — 2115 koşu, hatasız — çalıştırıldıktan sonra `demand_shift_traffic`'i `direction_shift_traffic` ve `mixed_master_scenario` ile karşılaştırınca beklenenden daha nüanslı bir tablo çıktı:

| Senaryo | Değişen şey | Fixed | v1/v2 | v3 | Rolling-Horizon | RH'nin v3'e göre farkı |
|---|---|---:|---:|---:|---:|---|
| `direction_shift_traffic` | sadece **yön** | 20.26 | 13.20 | 12.05 | **9.65** | RH açık ara en iyi (-%52 vs fixed) |
| `demand_shift_traffic` | sadece **büyüklük** | 16.65 | 11.49 | 11.19 | **11.13** | RH ile v3 istatistiksel olarak ayırt edilemez (std ~1.4-1.7) |
| `mixed_master_scenario` | yön + büyüklük birlikte (+emergency) | 23.15 | 26.35 | 31.45 | **35.30** | RH en kötüsü (-%53 vs fixed) |

(`avg_wait`, saniye; n=20 standart senaryolarda, n=3 mixed_master'da.)

**Yorum — hipotez kısmen doğrulandı, tam açıklamıyor:** Net bir kademe var. Yön değişimi tek başına rolling-horizon'u güçlendiriyor (fazladan öğrenilen parametre burada faydalı). Büyüklük değişimi tek başına ise RH'nin normalde sahip olduğu avantajı **sıfırlıyor** (v3 ile pratik olarak eşitleniyor) ama **negatife düşürmüyor**. Yani "öğrenilen parametre sayısı arttıkça rejim-değişimi hassasiyeti artar" hipotezi doğru yönde ama `demand_shift_traffic`'teki etkinin büyüklüğü, `mixed_master_scenario`'daki tam tersine dönüşü açıklamaya yetmiyor.

Bu, `mixed_master_scenario`'daki asıl tersine dönüşün saf büyüklük-rejim-değişiminden değil, muhtemelen şunlardan birinin veya birkaçının bileşiminden kaynaklandığını gösteriyor:
- yön ve büyüklüğün **aynı anda** değişmesi (iki eksenin etkileşimi, her biri tek başına olduğundan daha yıkıcı olabilir),
- emergency vehicle etkileşimi (`demand_shift_traffic`'te emergency kapalıydı, `mixed_master`'da açık — emergency preemption'ın rejim-değişimi sırasında öğrenmeyi ek olarak bozması mümkün),
- veya 20 farklı bloğun çeşitliliği/genişliği (v/c 0.15-0.90 arası geniş aralık, 4 blokluk basit sparse↔peak salınımından çok daha zengin bir örüntü kümesi).

Bu üç olası neden ayrı ayrı test edilmeden (ör. yön+büyüklük birlikte ama emergency kapalı bir senaryo, ya da emergency açık bir `demand_shift_traffic` varyantı), `mixed_master_scenario`'daki tersine dönüşün kök nedeni kesin olarak izole edilmiş sayılamaz. Gelecekteki bir rejim-değişimi-adaptasyonu mekanizması tasarlanırken bu üç aday da göz önünde bulundurulmalı.

## 2026-07-24: Gerçek Dünya Kalibrasyonu

### Bulgu: motorun kendi ölçtüğü kapasite (~1.116 araç/sn), gerçek kavşaklardan ~2.3x hızlıydı

Kullanıcı 3 farklı kavşakta 5-10 dakikalık kayıt aldı (tek yön/kamera, 4 yön aynı anda görünmüyor). Her yeşil faz için elle işaretlenen `(yeşil_başlangıç, ilk_araç_geçiş, yeşil_bitiş, boşalan_araç_sayısı, şerit_sayısı)` verisi `data/real_world_calibration.csv`'ye girildi (22 faz, 3 kavşak, `tools/real_world_calibration_analysis.py` ile analiz edildi):

- **Gerçek discharge_rate** (yön başına, 2 şeritli yollar, n=18 faz): ortalama **0.474 veh/s** (medyan 0.487, min 0.111, maks 0.625).
- **Gerçek start-up lost time** (yeşile geçiş ile ilk aracın hareketi arası gecikme, n=22): ortalama **~2.95s** (medyan 3.00s, aralık 2-5s).

Bunu doğrudan karşılaştırmak için `tools/measure_current_capacity.py` yazıldı — tek yönü sürekli yeşilde tutup doygun talep altında (fixed-time controller, `green_time` ≫ `simulation_time`) kaç araç boşalttığını ölçüyor. Motorun **değiştirilmemiş** haliyle sonucu: **1.083 veh/s** (3 seed ortalaması) — eski dokümante edilmiş ~1.116 ile %3 fark, yani eski rakam gerçekten bu yöntemle (ya da ona çok yakın bir yöntemle) üretilmiş. Ama gerçek veriyle (0.474) karşılaştırınca motor **~2.3x fazla iyimser**.

### Kök neden ve düzeltme

`simulation/vehicle.py` incelemesi `docs/engine_overview.md`'de zaten belgelenmiş bir basitleştirmeyi doğruladı: *"Araçlar sabit hızla hareket eder... ivme/yavaşlama/car-following fiziği yoktur."* Bir araç, önündeki boşaldığı anda **anında** tam hıza geçiyordu — gerçek dünyadaki reaksiyon/ivmelenme gecikmesi hiç modellenmiyordu. İki değişiklik yapıldı:

1. **`engine.startupLostTime = 3.0`** (yeni) — `SimulationEngine.is_effectively_green(direction_number, direction_name)` eklendi: sinyal durumu (render/karar için) hâlâ anında yeşile geçiyor, ama bir aracın **hareket edebilmesi** için mevcut yeşil fazın üzerinden `startupLostTime` kadar geçmiş olması gerekiyor (`engine.active_phase_tracking`'in `start_time`'ına göre ölçülüyor). `Vehicle.move()` ve `Vehicle.update_signal_wait_time()` artık `controller.is_green()` yerine bunu çağırıyor — `waitingDueToSignalQueue` sinyali de bu gecikme boyunca doğru şekilde "bekliyor" kalıyor.
2. **`engine.movingGap`: 25 → 215** — sürekli-akış sırasında araçlar arası takip mesafesi. `tools/measure_current_capacity.py` ile ampirik bir hassasiyet taraması yapıldı (`movingGap` değeri kapasiteyi güçlü ve öngörülebilir şekilde etkiliyor, `stoppingGap`/hız gibi diğer adaylardan çok daha surgical bir kaldıraç); 215 değeri gerçek 0.474 veh/s hedefine (**0.478 veh/s** ölçüldü, %1 fark) en yakın nokta.

Her iki değişiklik de sadece `simulation/engine.py` ve `simulation/vehicle.py`'de — strateji dosyalarına dokunulmadı, `discharge_rate` öğrenimi hâlâ tamamen motorun kendi (artık gerçekçi) fizik davranışından geliyor.

**Determinizm:** `tools/verify_determinism.py`'nin `[1]` testi (aynı seed, yüksüz, iki kez) değişiklik sonrası da birebir aynı kaldı. `[2]` testi (yapay CPU yükü altında) hem değişiklik ÖNCESİ hem SONRASI aynı büyüklükte (~tek tick) sapma gösterdi — bu, dosyanın başında bahsedilen, önceden kabul edilmiş spawner-thread istisnasının kendisi, yeni bir regresyon değil (doğrudan karşılaştırılarak doğrulandı).

### Senaryo yeniden kalibrasyonu: sabit oranla ölçekleme

v/c hedefleri (yukarıdaki tablo, 0.15-0.90) aynı kaldı; sadece bu hedefleri üreten `spawn_interval` değerleri yeni kapasiteye göre yeniden hesaplandı: `yeni_spawn_interval = eski_spawn_interval × (1.116 / 0.478) = eski_spawn_interval × 2.3347`. Bu, `data/scenarios.json`'daki 22 senaryonun tümüne (ve `demand_shift_traffic`/`mixed_master_scenario`'nun `dynamic_spawn_interval_schedule` bloklarına) uygulandı; `core/config_defaults.py`'nin fallback `spawn_interval`'ı da (1.63 → 3.81) aynı oranla güncellendi.

**Not — `sparse_traffic` tutarsızlığı (2026-08-22'de düzeltildi):** Bu ölçekleme sırasında `sparse_traffic`'in kendi `spawn_interval`'ının (ölçekleme öncesi 1.0, v/c≈0.90'a denk) yukarıdaki tabloda hedeflenen 4.48 (v/c≈0.20) ile uyuşmadığı fark edildi — `emergency_sparse_traffic` ve `mixed_master_scenario`/`demand_shift_traffic`'in "sparse" blokları doğru değeri kullanıyordu. Ölçekleme bunu mekanik olarak taşıdı (1.0 → 2.33) ve `batch_20260724_024258`'in `sparse_traffic` satırları bu hatalı (fiilen peak) değerle üretildi. Düzeltme ve yeniden ölçüm için aşağıdaki "2026-08-22: `sparse_traffic` düzeltmesi" bölümüne bakın.

### Doğrulama: pilot + tam batch (2026-07-24, `batch_20260724_024258`)

Değişiklik sonrası önce 1-seed'lik pilot (22 senaryo × 6 kontrolcü = 132 koşu, hatasız, adaptive 22 senaryonun 22'sinde de fixed'ten iyi), sonra tam batch (22 senaryo × 6 kontrolcü × 20 seed, mixed_master 3 seed — 2538 koşu, hatasız) çalıştırıldı. Rapor: `reports/batch_20260724_024258+batch_20260822_125454_report_20260822_132528/` (2026-08-22'de `sparse_traffic` düzeltmesi sonrası, iki batch'in birleşik raporu — aşağıdaki tabloda `sparse_traffic` satırı `batch_20260822_125454`'ten, diğer 21 satır `batch_20260724_024258`'ten gelir).

`overall_avg_wait`, fixed'e karşı en iyi adaptive kontrolcü:

| Senaryo | Fixed | En iyi adaptive | İyileşme | p99 iyileşme |
|---|---:|---:|---:|---:|
| balanced_traffic | 24.17 | 18.34 (v3) | %24.1 | %24.8 |
| right_heavy_traffic | 28.28 | 15.66 (v3) | %44.6 | %43.6 |
| vertical_heavy_traffic | 25.11 | 15.48 (RH-v2) | %38.4 | %23.3 |
| peak_traffic | 27.33 | 24.48 (v3) | %10.4 | %14.8 |
| low_traffic | 21.76 | 10.79 (RH-v2) | %50.4 | %49.8 |
| turn_heavy_traffic | 24.39 | 18.53 (v3) | %24.0 | %25.1 |
| single_direction_traffic | 46.96 | 0.00 (v3) | %100 | %100 |
| extreme_directional_traffic | 40.03 | 4.56 (v3) | %88.6 | %79.9 |
| sparse_traffic | 20.09 | 3.60 (RH-v1) | %82.1 | %80.6 |
| idle_intersection | 18.86 | 6.18 (v3) | %67.2 | %70.1 |
| direction_shift_traffic | 29.34 | 12.88 (v3) | %56.1 | %50.0 |
| demand_shift_traffic | 21.07 | 16.93 (v3) | %19.6 | %11.3 |
| burst_traffic | 27.55 | 19.17 (v3) | %30.4 | %33.6 |
| alternating_heavy_traffic | 26.48 | 16.09 (v3) | %39.2 | %44.9 |
| asymmetric_peak_traffic | 29.92 | 22.49 (RH-v2) | %24.8 | %15.2 |
| turning_conflict_traffic | 27.76 | 18.46 (RH-v2) | %33.5 | %25.6 |
| emergency_balanced_traffic | 18.79 | 6.77 (RH-v2) | %64.0 | %71.4 |
| emergency_right_heavy_traffic | 27.46 | 15.69 (v3) | %42.8 | %43.4 |
| emergency_peak_traffic | 28.85 | 24.12 (RH-v1) | %16.4 | -%1.1 |
| emergency_sparse_traffic | 22.17 | 5.21 (v3) | %76.5 | %74.8 |
| emergency_low_frequency_mixed_traffic | 27.00 | 18.46 (RH-v1) | %31.6 | %16.7 |
| mixed_master_scenario | 120.03 | 41.04 (RH-v1) | %65.8 | %58.6 |

**Not — mutlak sayılar artık daha yüksek, bu beklenen ve doğru:** Kapasite gerçek dünyaya göre düşürüldüğü için (~2.3x), her senaryonun mutlak `avg_wait`'i de büyüdü — bu senaryoların artık gerçek kavşaklara daha yakın bir zaman ölçeğinde çalıştığının işareti, bir regresyon değil. **22 senaryonun 22'sinde de adaptive fixed'ten iyi** — hiçbir gerileme yok, kalibrasyon-öncesi genel örüntü (bkz. yukarıdaki bölümler ve `docs/ground_truth_final_state_and_gaps.md`) korunmuş.

**Dikkat çekici bir iyileşme — `mixed_master_scenario` artık pozitif:** Bu dokümanın yukarıdaki (2026-07-16) bölümünde `mixed_master_scenario`'da adaptive'in fixed'ten **kötü** çıktığı (rejim-değişimi adaptasyon gecikmesi hipoteziyle açıklanan) bir bulgu vardı. Gerçek-dünya kalibrasyonu sonrası bu artık **tersine döndü** — rolling-horizon %65.8 iyileşme veriyor, hiçbir kontrolcü fixed'ten kötü değil. Kesin nedeni bu oturumda izole edilmedi (aday açıklamalar: daha yavaş/gerçekçi discharge_rate'in EMA öğreniminin rejim değişimlerine göreceli olarak daha az duyarlı hale gelmesi, ya da `startupLostTime`'ın kısa fazlarda stabilize edici bir taban oluşturması) — ileride bu eksen tekrar araştırılabilir, ama pratik sonuç: eski "rejim-değişimi zayıflığı" artık gözlenmiyor.

### Eski batch verisinin arşivlenmesi

Bu değişiklikten önce üretilmiş TÜM veri (motor fiziği ve `spawn_interval`'lar farklıydı) artık geçersiz. `data/batches/manual_runs.jsonl` (68 kayıt, 2026-07-19 ile 2026-07-23 arası manuel GUI test oturumlarından) ve `data/results_index.json`'daki karşılık gelen 68 satır, projenin kurulu arşivleme desenine göre `../traffic_sim_data_archive/pre_real_world_calibration_20260724/`'e taşındı (bkz. o klasördeki `NOTE.md`). Hiçbir şey silinmedi, sadece canlı/varsayılan yoldan çıkarıldı. Canlı `data/results_index.json` artık yalnızca `batch_20260724_024258`'in 2538 kaydını içeriyor. *(2026-08-22 güncellemesi: bu 2538 kaydın `sparse_traffic`'e ait 120'si hatalı senaryo kaydıyla üretildiği için `../traffic_sim_data_archive/stale_sparse_traffic_20260822/`'ye taşındı ve yerini `batch_20260822_125454`'ün 120 kaydı aldı — bkz. aşağıdaki bölüm.)*

## 2026-08-22: `sparse_traffic` düzeltmesi

### Sorun

`data/scenarios.json`'daki `sparse_traffic` kaydı, 2026-07-16 ile 2026-07-24 arasında bir noktada (büyük olasılıkla bir senaryo-editörü GUI oturumunda) yanlışlıkla üzerine yazılmıştı. Arşivdeki 2026-07-16 kopyası (`../traffic_sim_data_archive/scenarios_pre_capacity_recalibration_20260716.json`) ile karşılaştırılınca iki alanın saptığı doğrulandı:

| Alan | Hatalı değer (2026-07-24 batch'inde kullanılan) | Amaçlanan değer (2026-08-22'de geri alındı) |
|---|---:|---:|
| `config.spawn_interval` | 2.33 (v/c≈0.90 — fiilen *peak* yükü) | **10.46** (v/c≈0.20; `emergency_sparse_traffic` ve `mixed_master_scenario`/`demand_shift_traffic`'in "sparse" bloklarıyla aynı) |
| `config.vehicle_speeds.car` | 2.25 | **1.25** (proje geneli varsayılan; 2026-07-16 arşiv kopyasında `sparse_traffic` de 1.25'ti) |

Yani 2026-07-24 tablosundaki eski `sparse_traffic` satırı (fixed 28.42 / v3 14.89, %47.6) aslında "sparse" bir senaryoyu değil, hızlı arabalı bir peak senaryosunu ölçüyordu — `emergency_sparse_traffic`'ten (fixed 22.17 / 5.21) bu kadar farklı çıkmasının nedeni de buydu.

### Yapılanlar

1. `data/scenarios.json` — `sparse_traffic.config.spawn_interval` 2.33 → 10.46, `vehicle_speeds.car` 2.25 → 1.25. Başka hiçbir senaryo/alan değişmedi; motor/kontrolcü/strateji koduna dokunulmadı.
2. Eski `sparse_traffic` sonuçları (120 batch satırı + 2 manuel GUI koşusu) canlı `data/batches/*.jsonl` ve `data/results_index.json`'dan çıkarılıp `../traffic_sim_data_archive/stale_sparse_traffic_20260822/`'ye taşındı (bkz. oradaki `NOTE.md`; index'in silme-öncesi anlık görüntüsü de orada). Hiçbir şey silinmedi. `batch_20260724_024258`'in diğer 21 senaryosu olduğu gibi canlı kaldı.
3. 1-seed pilot (6 kontrolcü, hatasız) sonrası `sparse_traffic` aynı matrisle (6 kontrolcü × 20 seed = 120 koşu, `tools/run_batch_tests.py`'nin `SCENARIO_IDS`'i daraltılarak) yeniden koşuldu: **`batch_20260822_125454`**, 0 hata.
4. İki batch'in birleşik raporu üretildi: `reports/batch_20260724_024258+batch_20260822_125454_report_20260822_132528/` (`tools/report_generator.py`'nin `load_results`'ı yalnızca bu iki batch dosyasıyla beslendi — varsayılan `batch_run_id=None` modu `manual_runs.jsonl`'ı da katacağı için bilinçli olarak kullanılmadı). Eski tek-batch raporu `reports/batch_20260724_024258_report_20260724_144738/` artık hatalı `sparse_traffic` satırları içerdiğinden aynı arşiv klasörüne taşındı.

### Sonuç (`sparse_traffic`, 20 seed, `overall_avg_wait`)

| Kontrolcü | Avg wait | p99 | Queue peak | Crossed |
|---|---:|---:|---:|---:|
| fixed | 20.09 | 40.56 | 4.35 | 9.65 |
| v1 / v2 / v3 (özdeş) | 3.64 | 8.25 | 2.00 | 10.95 |
| RH-v1 | **3.60** | **7.86** | 2.00 | 10.95 |
| RH-v2 | 3.64 | 8.25 | 2.00 | 10.95 |

Fixed'e karşı en iyi iyileşme **%82.1** (p99 **%80.6**) — artık `emergency_sparse_traffic` (fixed 22.17 / 5.21, %76.5) ile aynı bantta, senaryo ismi ("sparse") ile ölçülen davranış tutarlı. Yukarıdaki 2026-07-24 tablosundaki `sparse_traffic` satırı bu yeni sayılarla güncellendi; 22/22 "adaptive fixed'ten iyi" sonucu korunuyor.
