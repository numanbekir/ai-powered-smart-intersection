# AI-Powered Smart Intersection: Proje Özeti

## Amaç

Tek bir kavşakta üç kontrol biçimi aynı senaryolarda karşılaştırılır:

1. Sabit süre: her yön sırayla aynı süre yeşil alır.
2. Adaptif, tam bilgi: karar kuralı kamera karesindeki araçların kesin sayısıyla çalışır.
3. Adaptif, kamera: aynı karar kuralı yalnızca YOLO11n tespitleriyle çalışır.

İkinci ve üçüncü arasındaki fark, kavşağı kamerayla algılamanın kontrol kalitesine maliyetidir.

## Mimari

```
Arayüz (Tkinter)  →  Kontrolcü  →  Gözlem kaynağı  →  Simülasyon motoru  →  Kayıt (JSON)
```

- Arayüz (`ui/`): simülasyon başlatma, senaryo seçimi ve düzenleme, kontrolcü seçimi.
- Kontrolcü (`controllers/`): `fixed_time_controller.py` ya da `adaptive_controller.py`. Adaptif kontrolcü zamanlamayı yürütür, kararı `strategies/demand_strategy.py` verir. Bkz. `docs/strategy_structure.md`.
- Gözlem kaynağı (`state_providers/`): `ground_truth_provider.py` kesin sayıyı, `yolo_provider.py` kamera karesindeki tespitleri verir. İkisi aynı görüş alanını kullanır.
- Simülasyon motoru (`simulation/`): araç doğuşu, hareket, sinyal fazları, metrikler, panel. Bkz. `docs/engine_overview.md`.
- Kayıt (`core/`, `data/*.json`): senaryolar, kontrolcü tanımları ve koşu sonuçları.

## Senaryolar ve deney düzeni

`data/scenarios.json` içinde 22 senaryo vardır: dengeli, yön ağırlıklı, yoğun, seyrek, yoğunluğu koşu içinde değişen ve acil durum araçlı türler, ayrıca hepsini art arda çalıştıran 30 dakikalık `mixed_master_scenario`. Yoğunlukların nasıl ayarlandığı `docs/scenario_capacity_calibration.md` dosyasındadır.

Her koşu senaryo, kontrolcü ve tohum üçlüsüyle tanımlanır ve bu üçlü sabitken sonuç birebir aynıdır. Sonuç tabloları `tools/baseline_sweep.py` ile üretilir: senaryo başına 10 tohum, 10 dakikalık koşular, ilk 2 dakika ısınma. Sabit süre altı farklı yeşil süresiyle taranır ve adaptif kontrol her senaryonun en iyi sabit süresiyle karşılaştırılır.

## Belgeler

- `docs/engine_overview.md`: motorun işleyişi, hareket modeli, determinizm.
- `docs/strategy_structure.md`: karar kuralı ve parametreleri.
- `docs/metrics_definitions.md`: metrik tanımları.
- `docs/scenario_capacity_calibration.md`: kapasite ölçümü, senaryo yoğunlukları, gerçek kayıtlarla ilişki.
- `docs/results_and_limits.md`: sonuç tabloları ve modelin kapsamadığı şeyler.
