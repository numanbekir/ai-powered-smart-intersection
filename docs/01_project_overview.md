# Proje Özeti

## Amaç

Bu proje, tek bir kavşakta **sabit süreli (fixed-time)** trafik ışığı kontrolü ile **adaptif (trafiğe duyarlı)** kontrolü karşılaştırmak, ve nihayetinde adaptif kontrolü **gerçek zamanlı kamera/YOLO tabanlı araç tespiti** ile çalışır hale getirmek için kurulmuş bir araştırma platformudur.

Proje üç aşamalı bir yol haritası izliyor:

1. **Sabit süreli kontrolü modellemek** — tamamlandı, referans/karşılaştırma noktası.
2. **Adaptif algoritma geliştirmek ve doğrulamak** — tamamlandı. Ground truth (tam bilgi) için kuyruk teorisine dayanan iki strateji ailesi: `optimal_ground_truth` (v1/v2/v3, tek-adım) ve `rolling_horizon_ground_truth` (çok-adım). Bkz. `docs/ground_truth_final_state_and_gaps.md`.
3. **Kamera tespitiyle kontrol (YOLO)** — tamamlandı. Simülasyon karelerinden veri kümesi üretildi, YOLO11n eğitildi, `yolo` provider ve `camera_queue` stratejisi yazıldı. Sonuçlar README'de ve `reports/camera/summary.md`'de.

## Mimari (üstten alta)

```
UI (Tkinter, 3 sekme)  →  Controller (fixed / adaptive)  →  State Provider  →  Simulation Engine  →  Persistence (JSON)
```

- **UI** (`ui/`): `Home` (simülasyon başlatma), `Scenarios` (senaryo seçimi + JSON ile yeni senaryo oluşturma), `Providers` (solda provider type, sağda o tipe uyumlu stratejiler).
- **Controller** (`controllers/`): `fixed_time_controller.py` (statik döngü) veya `adaptive_controller.py` (bir `strategy`'ye delege eder — bkz. `docs/strategy_structure.md`).
- **State Provider** (`state_providers/`): controller'ın trafik durumunu *nasıl gördüğünü* belirler.
  - `ground_truth_provider.py`: tüm araçları eksiksiz görür (ideal/tam bilgi).
  - `yolo_provider.py`: kavşağın 900x900 üstten karesini (`simulation/camera.py`) simülasyon saniyesinde bir kez YOLO modeline verir. Her yön için duran araç sayısını ve tespit edilen acil durum aracını bildirir. Araçların kendisinden hiçbir şey okumaz, kare dışını görmez.
- **Simulation Engine** (`simulation/engine.py`): araç doğuşu, hareket, sinyal fazları, metrik toplama. Detaylar için `docs/engine_overview.md`.
- **Persistence** (`core/`, `data/*.json`): senaryolar, kontrolcü versiyonları, provider'lar ve deney sonuçları JSON registry'ler üzerinden saklanır.

## Şu anki durum

| Katman | Durum |
|---|---|
| Fixed-time controller | Sağlam, değişmedi |
| `ground_truth` provider | Sağlam, tam bilgi sağlıyor |
| `ground_truth` stratejisi | `optimal_ground_truth` (v1/v2/v3) + `rolling_horizon_ground_truth` — bkz. `docs/strategy_structure.md`, `docs/ground_truth_final_state_and_gaps.md` |
| `yolo` provider | Çalışıyor. Ağırlık `weights/vehicle_detector.pt`, ek paketler `requirements-yolo.txt` |
| `yolo` stratejisi | `camera_queue` (`adaptive_camera_queue_v1`) — v3'ün karar kuralı, girdisi yalnızca tespitler. Bkz. `docs/strategy_structure.md` |

Ground_truth hattının sonuçları kameralı kontrolün ölçüldüğü **tavan** olarak `docs/ground_truth_final_state_and_gaps.md`'de duruyor. Kameralı kontrol bu tavana ortanca 1,2 sn ek beklemeyle yaklaşıyor, kuyruğun kare dışına taştığı senaryolarda fark 5,6 sn'ye çıkıyor. Görüntüler simülasyonun kendi çizimi olduğu için bu sonuç tespit hatalarını değil, sınırlı görüş alanını ve bir saniyelik gözlem aralığını ölçer.

## Senaryolar ve deney metodolojisi

`data/scenarios.json` içinde 20 sabit senaryo (dengeli, yön-ağırlıklı, yoğunluk varyantları, 5 emergency-araç varyantı) artı `mixed_master_scenario` — bu 20 senaryonun tümünü rastgele sırayla, 90'ar saniyelik fazlar halinde birleştiren, 30 dakikalık uzun/rejim-değişimli bir stres testi. Her deney **(senaryo, kontrolcü, seed)** üçlüsüyle tanımlanır ve bu üçlü sabitken deterministik olması beklenir (bkz. `docs/engine_overview.md` §Determinizm). `tools/run_batch_tests.py` bu matrisi headless çalıştırıp `tools/report_generator.py` ile rapor üretir.

## Dokümantasyon haritası

**Güncel referans (kökte):**
- `docs/engine_overview.md` — simülasyon motorunun çalışma mantığı.
- `docs/strategy_structure.md` — `controllers/strategies/` klasör yapısı, `base_strategy.py`, `optimal_ground_truth_strategy.py`, `rolling_horizon_ground_truth_strategy.py`.
- `docs/metrics_definitions.md` — her metriğin tanımı ve bilinen metodolojik notlar.
- `docs/scenario_capacity_calibration.md` — ölçülen sistem kapasitesi, tüm senaryoların gerçekçi v/c kalibrasyonu.
- `docs/ground_truth_final_state_and_gaps.md` — ground_truth hattının nihai metrik tavanı, sistemin gerçek trafikte karşıladığı/kapsamadığı şeylerin somut listesi.

`optimal_ground_truth` ailesinin v1→v2→v3 tasarım/bugfix sürecini, rolling-horizon v1 vs v2 A/B sonucunu ve bu süreçlerin ilk (kalibrasyon-öncesi) batch kanıtlarını belgeleyen tarihsel dokümanlar artık bu projenin bir parçası değil — `../traffic_sim_docs_archive/`'a taşındı (içindeki negatif/nötr bulgular, ör. RH v2'nin ölçülebilir bir kazanç sağlamadığı, gerçek araştırma değeri taşıdığı için tamamen atılmadı, ama günlük geliştirme için gerekli olmadığından ve güncel sayılar için zaten yukarıdaki dosyalar yeterli olduğundan projeden çıkarıldı).

Bu proje, kendisinden önceki uzun bir deneysel/keşif sürecinden (onlarca strateji versiyonu denenmiş bir evrim) izole edilmiştir: o sürecin kodu ve dokümantasyonu `../traffic_sim_fazlalik/` altında tarihsel arşiv olarak duruyor, ama güncel proje bunlardan hiçbirine bağımlı değil ve referans vermiyor. Güncel çalışma için yukarıdaki dosyalar yeterli ve günceldir.
