# Trafik Işığı Simülasyonu — Sabit Süreli vs Adaptif Kontrol

Tek kavşaklı bir trafik ışığı simülasyonu (Tkinter + pygame). Sabit süreli
(fixed-time) kontrolü, kuyruk teorisine dayanan adaptif kontrolcülerle
karşılaştırıyor; nihai hedef gerçek YOLO/CV tabanlı araç algılamasını
entegre etmek.

![Adaptif kontrolcü dengeli trafik senaryosunda](docs/ekran-goruntusu.png)

## Proje üç aşamalı bir yol haritası izliyor

1. **Sabit süreli kontrolü modellemek** — tamamlandı, referans/karşılaştırma noktası.
2. **Adaptif algoritma geliştirmek ve doğrulamak** — tamamlandı. Kuyruk teorisine
   dayanan, gerekçeli bir strateji ailesi (`optimal_ground_truth` v1/v2/v3,
   `rolling_horizon_ground_truth`), 22 senaryo × 20 seed'lik batch testleriyle
   fixed-time'a karşı doğrulandı — 22 senaryonun tamamında net kazanç
   (%17-100 ortalama bekleme iyileşmesi). Detay: `docs/ground_truth_final_state_and_gaps.md`.
3. **Gerçek zamanlı algılama (YOLO/CV) entegrasyonu** — henüz başlamadı,
   bir sonraki hedef.

## Mimari

```
UI (Tkinter, 3 sekme)  →  Controller (fixed / adaptive)  →  State Provider  →  Simulation Engine  →  Persistence (JSON)
```

- **UI** (`ui/`): `Home` (simülasyon başlatma), `Scenarios` (senaryo seçimi
  + JSON ile yeni senaryo oluşturma), `Providers` (kontrolcü/strateji seçimi).
- **Controller** (`controllers/`): `fixed_time_controller.py` ya da
  `adaptive_controller.py` (ortak faz mekaniğini kendisi yönetir, karar
  mantığını `controllers/strategies/`'e delege eder).
- **State Provider** (`state_providers/`): controller'ın trafik durumunu
  *nasıl gördüğünü* belirler — `ground_truth` (tam bilgi, tüm araçları
  hatasız görür) ya da `yolo` (gerçek kamera/YOLO algılamanın yer tutucusu,
  henüz uygulanmadı).
- **Simulation Engine** (`simulation/engine.py`): araç doğuşu, hareket,
  sinyal fazları, metrik toplama, render veya headless çalışma. İki thread
  + tek otoriter saat modeliyle **deterministik** çalışır — aynı
  (senaryo, kontrolcü, seed) her zaman birebir aynı sonucu üretir.
- **Persistence** (`core/`, `data/*.json`): senaryolar, kontrolcü
  versiyonları, provider'lar ve deney sonuçları JSON registry'ler
  üzerinden saklanır.

## Kurulum ve çalıştırma

Gerekenler: Python 3.10+, `pygame`, `matplotlib`.

```bash
pip install -r requirements.txt

# GUI uygulamasını başlat
python main.py

# Tüm senaryo × kontrolcü × seed matrisini headless çalıştır, rapor üret
python tools/run_batch_tests.py

# Determinizm garantisini doğrula
python tools/verify_determinism.py

# En son batch'ten markdown + PNG rapor üret
python tools/report_generator.py
```

## Mevcut durum

| Katman | Durum |
|---|---|
| Fixed-time controller | Sağlam, referans noktası |
| `ground_truth` provider + strateji ailesi | Sağlam, kapsamlı batch veriyle doğrulanmış. Önerilen: `adaptive_optimal_ground_truth_v3` (tek-adım), `adaptive_rolling_horizon_ground_truth` (çok-adım) |
| `yolo` provider | Placeholder — gerçek algılama henüz yok |

## Dokümantasyon

Detaylı (Türkçe) dokümantasyon `docs/` altında — özellikle:

- `docs/01_project_overview.md` — proje amacı, yol haritası, genel mimari (başlangıç noktası).
- `docs/engine_overview.md` — simülasyon motorunun iç işleyişi, determinizm.
- `docs/strategy_structure.md` — adaptif strateji sözleşmesi, yeni strateji ekleme.
- `docs/metrics_definitions.md` — her metriğin tanımı ve bilinen metodolojik notlar.
- `docs/scenario_capacity_calibration.md` — senaryo talep kalibrasyonu (güncel referans).
- `docs/ground_truth_final_state_and_gaps.md` — **YOLO fazından önce okunacak**: nihai metrik tavanı, sistemin gerçek trafikte karşıladığı/kapsamadığı şeyler.

## Determinizm

`(senaryo, kontrolcü modu, kontrolcü versiyonu, state provider, seed)`
beşlisi sabitken simülasyon birebir deterministiktir. Motor/kontrolcü/
strateji tarafında yapılan herhangi bir değişiklikten sonra
`python tools/verify_determinism.py` çalıştırılmalı.
