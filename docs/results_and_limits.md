# Sonuçlar ve Sınırlar

Bu belge üç kontrolcünün 22 senaryodaki tam sonuç tablolarını ve
simülasyonun gerçek bir kavşağa göre neleri basitleştirdiğini içerir.

## Yöntem

- Koşu 600 sn, ilk 120 sn ısınma. `mixed_master_scenario` kendi süresiyle
  (1800 sn) koşulur.
- Senaryo başına 10 tohum, `mixed_master_scenario` için 3.
- Sabit süreli kontrol 6, 8, 10, 12, 15 ve 20 sn yeşillerle ayrı ayrı
  koşulur. Adaptif kontrol her senaryonun en iyi sabit süresiyle
  karşılaştırılır. Tek bir sabit süreye göre karşılaştırma adaptif kontrolü
  olduğundan iyi gösterir, çünkü en iyi sabit süre senaryodan senaryoya
  6 ile 20 sn arasında değişiyor.
- Bekleme, ölçüme giren bütün araçları kapsar: kavşağı geçenler ve koşu
  bittiğinde hâlâ kuyrukta olanlar (bkz. `docs/metrics_definitions.md`).
- Üç kontrolcü aynı senaryo ve tohumlarla koşulur. Araçların doğuşu
  kontrolcüden bağımsızdır, yani her kontrolcü birebir aynı trafiği görür.

Ham veri `reports/baseline_sweep/raw_results.csv` ve
`reports/camera/raw_results.csv`, özetler `tools/baseline_sweep_report.py`
ve `tools/camera_comparison_report.py` ile üretilir.

## Tam bilgili adaptif kontrol ve sabit süre

- Her senaryonun en iyi sabit süresine göre kazanç: ortanca %22, ortalama
  %35, en düşük -%7.
- Adaptif kontrol 22 senaryonun 20'sinde ortalamada önde, 18'inde koşuların
  en az %80'inde önde.
- Varsayılan sabit süreye (10 sn) göre kazanç ortalama %40. Bu sayı tek
  başına kullanılmamalı, yukarıdaki nedenle yanıltıcıdır.

Ortalama bekleme (sn):

| Senaryo | sabit 6s | sabit 8s | sabit 10s | sabit 12s | sabit 15s | sabit 20s | en iyi sabit | en iyi adaptif | kazanç (sabit 10s) | kazanç (en iyi sabit) | adaptif önde (koşu) | geçemeyen: sabit / adaptif |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| balanced_traffic | 25.2 | 21.4 | 22.4 | 23.4 | 25.9 | 30.6 | 8s | 19.9 | %11 | %7 | 6/10 | %7 / %6 |
| right_heavy_traffic | 52.6 | 52.6 | 53.8 | 51.9 | 55.9 | 56.9 | 12s | 21.5 | %60 | %59 | 10/10 | %24 / %8 |
| vertical_heavy_traffic | 54.6 | 46.6 | 42.4 | 41.6 | 40.0 | 42.1 | 15s | 18.2 | %57 | %55 | 10/10 | %15 / %5 |
| peak_traffic | 66.4 | 54.8 | 48.9 | 44.4 | 43.0 | 42.6 | 20s | 42.6 | %13 | %-0 | 5/10 | %14 / %16 |
| low_traffic | 14.6 | 15.9 | 17.7 | 20.6 | 23.6 | 28.6 | 6s | 12.5 | %29 | %15 | 10/10 | %4 / %4 |
| turn_heavy_traffic | 27.6 | 23.4 | 23.5 | 24.3 | 26.6 | 30.9 | 8s | 20.8 | %11 | %11 | 8/10 | %7 / %6 |
| single_direction_traffic | 39.3 | 52.3 | 64.3 | 72.8 | 87.6 | 108.7 | 6s | 0.0 | %100 | %100 | 10/10 | %91 / %1 |
| extreme_directional_traffic | 55.8 | 67.7 | 77.1 | 82.6 | 91.4 | 101.4 | 6s | 17.5 | %77 | %69 | 10/10 | %67 / %10 |
| sparse_traffic | 13.9 | 15.3 | 16.8 | 19.2 | 22.4 | 28.3 | 6s | 4.0 | %76 | %71 | 10/10 | %5 / %2 |
| idle_intersection | 12.3 | 13.4 | 16.6 | 18.3 | 23.4 | 25.9 | 6s | 3.6 | %79 | %71 | 10/10 | %4 / %3 |
| direction_shift_traffic | 28.7 | 23.4 | 23.2 | 23.9 | 26.6 | 31.0 | 10s | 20.0 | %14 | %14 | 9/10 | %7 / %6 |
| demand_shift_traffic | 26.8 | 22.4 | 22.9 | 23.3 | 26.3 | 30.6 | 8s | 20.6 | %10 | %8 | 9/10 | %7 / %6 |
| burst_traffic | 37.0 | 29.6 | 26.6 | 27.0 | 28.3 | 32.0 | 10s | 24.1 | %9 | %9 | 9/10 | %9 / %8 |
| alternating_heavy_traffic | 39.1 | 31.5 | 27.7 | 27.5 | 29.7 | 33.3 | 12s | 24.4 | %12 | %11 | 9/10 | %8 / %8 |
| asymmetric_peak_traffic | 71.5 | 75.2 | 77.3 | 78.2 | 79.6 | 82.4 | 6s | 51.7 | %33 | %28 | 10/10 | %54 / %28 |
| turning_conflict_traffic | 73.4 | 71.5 | 68.0 | 66.6 | 65.4 | 64.6 | 20s | 30.4 | %55 | %53 | 10/10 | %28 / %12 |
| emergency_balanced_traffic | 24.0 | 21.9 | 21.7 | 22.8 | 25.2 | 30.3 | 10s | 20.5 | %5 | %5 | 7/10 | %6 / %6 |
| emergency_right_heavy_traffic | 52.7 | 53.6 | 54.2 | 54.4 | 55.9 | 58.6 | 6s | 21.2 | %61 | %60 | 10/10 | %33 / %8 |
| emergency_peak_traffic | 66.5 | 54.9 | 48.7 | 43.3 | 41.7 | 42.9 | 15s | 44.7 | %8 | %-7 | 1/10 | %15 / %16 |
| emergency_sparse_traffic | 13.3 | 14.8 | 17.6 | 19.0 | 23.3 | 28.3 | 6s | 4.0 | %77 | %70 | 10/10 | %5 / %2 |
| emergency_low_frequency_mixed_traffic | 19.6 | 18.1 | 20.2 | 21.7 | 23.9 | 28.9 | 8s | 15.1 | %25 | %17 | 9/10 | %6 / %5 |
| mixed_master_scenario | 86.1 | 67.4 | 61.6 | 55.8 | 54.2 | 52.6 | 20s | 22.7 | %63 | %57 | 3/3 | %3 / %2 |

Tabloyu okurken:

- Kazanç trafiğin dengesizliğinden geliyor. Tek yönlü, aşırı yönlü, yön
  ağırlıklı, dönüş çakışmalı ve seyrek senaryolarda kazanç %53-100 ve
  koşuların hepsinde tekrarlanıyor. Talebin tek yöne yığıldığı asimetrik
  yoğun saatte kazanç %28. Sabit süre aracı olmayan yöne de yeşil
  veriyor.
- Dengeli trafikte fark küçük: iyi ayarlanmış sabit süreye göre %5-17,
  koşuların bir kısmında sabit süre önde.
- `peak_traffic` ve `emergency_peak_traffic`'te talep kapasitenin üstünde,
  araçların yaklaşık altıda biri koşu sonunda hâlâ kuyrukta. Burada en uzun
  sabit yeşiller (15-20 sn) adaptif kontrolle aynı düzeyde ya da önde.
  Kapasite yetmediğinde sırayı değiştirmek bir şey kazandırmıyor, uzun
  yeşil ise sarıda kaybedilen süreyi azaltıyor.
- `single_direction_traffic`'teki %100 bir kenar durumu: tek aktif yön
  sürekli yeşilde kalıyor.

## Kameralı kontrol

Kameralı kontrolcü tam bilgili kontrolcüyle aynı karar kuralını ve aynı
görüş alanını kullanır. Tek fark araç sayısının YOLO11n tespitlerinden
gelmesi ve gözlemin saniyede bir alınması.

- En iyi sabit süreye göre kazanç: ortanca %22, ortalama %36, en düşük -%8.
- Ortalamada sabit sürenin önünde olduğu senaryo: 22'de 21.
- Tam bilgiye göre fark (kamera eksi tam bilgi): ortanca -0,2 sn, en
  yüksek +1,1 sn.

| Senaryo | en iyi sabit | tam bilgi | kamera | kamera kazancı (en iyi sabit) | kameranın tam bilgiye göre kaybı | kamera önde (koşu) | geçemeyen: tam bilgi / kamera |
|---|---:|---:|---:|---:|---:|---:|---:|
| balanced_traffic | 21.4 (8s) | 19.9 | 19.4 | %10 | -0.6 sn | 7/10 | %6 / %6 |
| right_heavy_traffic | 51.9 (12s) | 21.5 | 21.1 | %59 | -0.5 sn | 10/10 | %8 / %8 |
| vertical_heavy_traffic | 40.0 (15s) | 18.2 | 18.0 | %55 | -0.1 sn | 10/10 | %5 / %5 |
| peak_traffic | 42.6 (20s) | 42.6 | 42.3 | %1 | -0.3 sn | 5/10 | %16 / %16 |
| low_traffic | 14.6 (6s) | 12.5 | 12.4 | %15 | -0.1 sn | 10/10 | %4 / %4 |
| turn_heavy_traffic | 23.4 (8s) | 20.8 | 20.2 | %14 | -0.7 sn | 9/10 | %6 / %6 |
| single_direction_traffic | 39.3 (6s) | 0.0 | 0.0 | %100 | +0.0 sn | 10/10 | %1 / %1 |
| extreme_directional_traffic | 55.8 (6s) | 17.5 | 16.8 | %70 | -0.7 sn | 10/10 | %10 / %9 |
| sparse_traffic | 13.9 (6s) | 4.0 | 4.2 | %70 | +0.2 sn | 10/10 | %2 / %2 |
| idle_intersection | 12.3 (6s) | 3.6 | 3.6 | %71 | +0.0 sn | 10/10 | %3 / %3 |
| direction_shift_traffic | 23.2 (10s) | 20.0 | 19.4 | %16 | -0.6 sn | 10/10 | %6 / %6 |
| demand_shift_traffic | 22.4 (8s) | 20.6 | 20.3 | %9 | -0.3 sn | 7/10 | %6 / %6 |
| burst_traffic | 26.6 (10s) | 24.1 | 24.3 | %9 | +0.2 sn | 9/10 | %8 / %8 |
| alternating_heavy_traffic | 27.5 (12s) | 24.4 | 24.4 | %11 | +0.1 sn | 9/10 | %8 / %7 |
| asymmetric_peak_traffic | 71.5 (6s) | 51.7 | 51.1 | %28 | -0.6 sn | 10/10 | %28 / %27 |
| turning_conflict_traffic | 64.6 (20s) | 30.4 | 29.4 | %55 | -1.0 sn | 10/10 | %12 / %11 |
| emergency_balanced_traffic | 21.7 (10s) | 20.5 | 20.2 | %7 | -0.3 sn | 8/10 | %6 / %6 |
| emergency_right_heavy_traffic | 52.7 (6s) | 21.2 | 20.3 | %62 | -1.0 sn | 10/10 | %8 / %7 |
| emergency_peak_traffic | 41.7 (15s) | 44.7 | 45.2 | %-8 | +0.4 sn | 1/10 | %16 / %16 |
| emergency_sparse_traffic | 13.3 (6s) | 4.0 | 4.0 | %70 | +0.0 sn | 10/10 | %2 / %2 |
| emergency_low_frequency_mixed_traffic | 18.1 (8s) | 15.1 | 15.2 | %16 | +0.1 sn | 10/10 | %5 / %4 |
| mixed_master_scenario | 52.6 (20s) | 22.7 | 23.7 | %55 | +1.1 sn | 3/3 | %2 / %2 |

İki adaptif kontrolcü arasındaki fark senaryo başına bir saniyenin
altında ve iki yöne de dağılıyor. Simülasyon görüntüsünde model neredeyse
hatasız olduğu için bu beklenen sonuç: tespit hataları kararı
değiştirmiyor. Bu, gerçek kamera görüntüsü için bir şey söylemez (bkz.
aşağıdaki sınırlar).

## Acil durum araçları

Acil durum araçlarının ortalama beklemesi (sn, kavşağı geçenler):

| Senaryo | en iyi sabit | tam bilgi | kamera |
|---|---:|---:|---:|
| emergency_balanced_traffic | 18.9 | 1.6 | 1.4 |
| emergency_right_heavy_traffic | 63.6 | 15.1 | 12.3 |
| emergency_peak_traffic | 50.1 | 23.0 | 19.9 |
| emergency_sparse_traffic | 17.9 | 0.3 | 0.8 |
| emergency_low_frequency_mixed_traffic | 18.0 | 1.0 | 1.4 |
| mixed_master_scenario | 54.6 | 7.4 | 8.6 |

Adaptif kontrolün en net üstünlüğü burada. `emergency_right_heavy_traffic`
ve `emergency_peak_traffic`'te bekleme daha yüksek. Bu senaryolarda kuyruk
karenin dışına taşabiliyor. Acil durum aracı kuyruğun arkasında kalınca
kontrolcü onu ancak kareye girdiğinde görebiliyor, öncelik de o zaman
başlıyor.

## Simülasyonun kapsadığı

- Aynı trafik altında tekrarlanabilir karşılaştırma. Senaryo, kontrolcü ve
  tohum sabitken sonuç birebir aynı (`tools/verify_determinism.py`).
- Kapasiteye oranla tanımlanmış talep seviyeleri: seyrek trafik v/c 0,20,
  dengeli 0,55-0,65, yoğun saat 0,90 (bkz.
  `docs/scenario_capacity_calibration.md`).
- Yön ağırlıklı, yoğunluğu koşu içinde değişen, dönüş çakışmalı ve acil
  durum araçlı senaryolar.
- İvmelenen, fren yapan ve öndeki aracı izleyen araçlar. Kuyruk sırayla
  çözülüyor (`tools/verify_vehicle_motion.py`).
- Görüntüden araç sınıfı tespiti ve bu tespitlerle verilen sinyal kararı.

## Simülasyonun basitleştirdiği

1. Görüntü sentetik. Kareler simülasyonun kendi çizimi: araçlar hep aynı
   ölçekte ve görünümde, ışık, hava, gölge, örtüşme ve kamera açısı yok.
   Gerçek görüntüde tespit hataları kontrol kalitesini bu sonuçlardan çok
   daha fazla etkileyecektir. Projenin bir sonraki adımı bu maliyeti
   gerçek görüntüyle ölçmek.
2. Görüş alanı sınırlı. Kontrolcü yalnızca 900x900 kareyi görüyor. Kare
   dışına taşan kuyruk sayılamıyor, kural kenara dayanan kuyruğa 3 sn ek
   yeşil vererek bunu kabaca telafi ediyor. Kare dışındaki acil durum aracı
   görülmüyor.
3. Kapasite gerçek kayıtlardan yüksek. Simülasyon yön başına 1,00 araç/sn
   boşaltıyor, üç gerçek kavşaktan alınan kayıtlarda bu değer 0,45 araç/sn.
   Senaryolar kapasiteye oranla tanımlandığı için kontrolcülerin
   karşılaştırması geçerli, ama saniye cinsinden süreler gerçek bir kavşağa
   doğrudan taşınamaz.
4. Talep sentetik. Varış aralıkları ve yön ağırlıkları tasarım kararı,
   gerçek bir kavşağın sayım verisiyle karşılaştırılmadı.
5. Tek kavşak. Araçlar kavşağı geçtikten sonra çıkış yolundan ayrılıyor,
   komşu kavşaktan geri taşan kuyruk ve yeşil dalga modellenmiyor.
6. Yaya fazı yok. 5 sn'lik en kısa yeşil gerçek bir kent kavşağına göre
   iyimser.
7. Aynı anda tek yön yeşil alıyor. Karşılıklı iki yönün birlikte geçtiği
   faz düzeni ve korumalı sol dönüş yok.
8. Sürücü davranışı tek tip. Bütün sürücüler aynı ivme, fren ve takip
   mesafesiyle sürüyor. Acil durum aracına her zaman yol veriliyor.
