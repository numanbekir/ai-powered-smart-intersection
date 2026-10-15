# Simülasyon Motoru (`simulation/engine.py`, `simulation/vehicle.py`)

`SimulationEngine` araç doğuşunu, hareketi, sinyal fazlarını, metrik toplamayı ve çizimi yürütür. Pencereli ve penceresiz (headless) çalışma aynı kodu kullanır.

## Çalışma zamanı: iki iş parçacığı, tek saat

Ana döngünün yanında iki iş parçacığı çalışır:

- Kontrolcü (`controller.run`): sinyal fazlarını seçer ve uygular.
- Araç üretici (`generateVehicles`): yeni araçları rastgele yön, tür ve dönüş niyetiyle üretir.

Zaman duvar saatiyle değil tek bir sayaçla (`simulation_elapsed`) ilerler. Her adımda sayaç `oynatma hızı / fps` kadar artar. `scaled_sleep()` gerçek zamanda uyumaz, sayacın hedefe ulaşmasını bekler. Böylece oynatma hızı ne olursa olsun aynı senaryo ve tohum aynı sonucu verir.

Ana döngü, iki iş parçacığı o adımdaki işini bitirip yeniden beklemeye geçmeden sonraki adıma ilerlemez (`wait_for_workers()`). İşlemci yükü altında da sonuç değişmez.

## Determinizm

Senaryo, kontrolcü, gözlem kaynağı ve tohum sabitken sonuç birebir aynıdır. `tools/verify_determinism.py` bunu art arda iki koşuyla ve yapay işlemci yükü altında denetler. Motorda, kontrolcüde ya da karar kuralında yapılan her değişiklikten sonra çalıştırılır.

## Hareket modeli

Araçlar ivmelenir, fren yapar ve öndeki aracı izler. Değerler piksel ve simülasyon saniyesi cinsindendir:

| Değer | Anlamı |
|---|---|
| `acceleration` = 25 | hızlanma |
| `comfortBraking` = 40 | olağan fren |
| `hardBraking` = 90 | ışık değiştiği anda duruş kararında kullanılan sert fren |
| `timeHeadway` = 0,7 | öndeki araçla bırakılan zaman aralığı |
| `startGap` = 5 | duran aracın kalkması için önünde açılması gereken boşluk |
| `stoppingGap` = 25 | duran araçlar arasındaki mesafe |
| `turnSpeedFactor` = 0,7 | dönüşteki hız oranı |

Kurallar:

- Takip: hız, öndeki boşluğun izin verdiği değeri aşmaz. Duran bir aracın arkasında yavaşlama fren eğrisiyle yapılır, uzun süre sürünerek yaklaşma olmaz.
- Kalkış: duran araç önünde `startGap` kadar boşluk açılmadan kalkmaz. Kuyruk tek blok hâlinde değil, sırayla çözülür.
- Dur çizgisi: ışık yeşil değilken araç çizgide durur. Işık değiştiği anda duramayacak kadar yakın olan araç geçer.
- Kavşak içi: ışık yeşil olsa da başka yönden gelen bir araç kavşak içindeyken çizgide beklenir.
- Dönüş: dönen araç aynı sabit yolu daha düşük hızla izler ve çıkış yolundaki araçları takip eder.

Ölçülen doygun kapasite yön başına 1,00 araç/sn'dir (iki şerit, şerit başına 2 sn'de bir araç). `tools/measure_current_capacity.py` ile ölçülür. `tools/verify_vehicle_motion.py` dört kuralı denetler: hız sıçrama yapmadan değişir, öndeki araç kalkınca arkadaki 1,5 sn içinde kalkar, önü boş olan araç durmaz, duran araçlar üst üste binmez.

Kapasitenin gerçek kavşak kayıtlarıyla ilişkisi için `docs/scenario_capacity_calibration.md`.

## Doğuş noktası

Araç, şeridin sabit doğuş noktasında ya da şeridin son aracı henüz oradan ayrılmadıysa onun arkasında doğar (`Vehicle.place_at_spawn()`).

## Simülasyon penceresi ayrı süreçte çalışır

Arayüz Tkinter, simülasyon penceresi pygame kullanır. İkisi aynı süreçte çalıştığında simülasyondan sonra açılan bir arayüz penceresi uygulamayı çökertiyordu. Simülasyon bu yüzden ayrı bir süreçte çalıştırılır (`simulation/runner.py`), sonuç ana sürece bir boru üzerinden döner.

## Sağ panel

`simulation/panel.py` pencerenin sağındaki paneli çizer: yön tablosu (ışık, araç sayısı, bekleme, geçen araç), son karar, koşu özeti ve son yeşiller. Kameralı kontrolde tabloda kameranın saydığı araç sayısı gösterilir, kesin sayıdan ayrıldığında fark ayrıca yazılır.

## Metrik toplama

Bekleme süresi, araç sinyal yüzünden dururken her adımda simülasyon saniyesi cinsinden birikir, oynatma hızından bağımsızdır. Tanımlar `docs/metrics_definitions.md` dosyasındadır.

## Bilinen sınırlar

- Tek kavşak modellenir. Koridor ya da ağ eşgüdümü denenemez.
- Yaya fazı yoktur. 5 sn'lik en kısa yeşil gerçek bir kent kavşağına göre iyimserdir.
- Aynı anda tek yön yeşil alır. Karşılıklı iki yönün birlikte geçtiği faz düzeni modellenmez.
- Üst üste binme denetimi dönüşün ortasındaki araçları kapsamaz.
- Kavşağı geçen araçlar bellekten silinmez. Çok uzun koşularda bellek kullanımı artar.
- Kuyruk uzunluğu adım başına ağırlıksız örneklenir. Farklı oynatma hızlarında alınan mutlak değerler birbiriyle karşılaştırılmaz.
