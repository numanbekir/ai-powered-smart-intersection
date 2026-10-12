# Simülasyon Motoru (`simulation/engine.py`, `simulation/vehicle.py`)

`SimulationEngine`, projenin çalışma zamanı çekirdeğidir: araç doğuşu, hareket/fizik, sinyal fazı yönetimi, metrik toplama, render (veya headless çalıştırma) hepsi buradan yürütülür. Bu doküman motorun nasıl çalıştığını ve neden bu şekilde tasarlandığını özetler.

## Çalışma zamanı yapısı: iki thread + tek otoriter saat

Motor iki thread çalıştırır:

- **Controller thread** (`self.controller.run`) — sinyal fazlarını seçer/uygular.
- **Spawner thread** (`self.generateVehicles`) — yeni araçları rastgele yön/tip/dönüş niyetiyle üretir.

İkisi de `engine.vehicles[direction][lane]` listesini paylaşır. Bu paylaşım, bu oturumda bulunan bir hataya kadar tehlikeliydi (aşağıya bakın).

Zaman, gerçek duvar-saatiyle değil, **tek bir otoriter sayaçla** (`simulation_elapsed`) ilerler: her ana döngü tick'i `advance_simulation_time()` ile `current_simulation_delta` kadar (= `(1/fps) * playback_speed`) artırılır. `scaled_sleep()` (controller ve spawner thread'lerinin "bekleme" ihtiyaçları için) gerçek zamanda uyumaz, bu sayacın hedefe ulaşmasını bekler. Bu tasarımın amacı: `playback_speed` ne olursa olsun (1x veya 8x), **aynı (senaryo, seed) aynı sonucu üretsin** — ana döngü CPU yükü altında yavaşlasa bile.

## Determinizm

`(senaryo, kontrolcü modu, kontrolcü versiyonu, state provider, seed)` beşlisi sabitken simülasyon deterministik olmalıdır (`random.seed(seed)`). `tools/verify_determinism.py` bunu doğrular: aynı seed'le, yapay CPU yükü olmadan art arda iki koşu **birebir aynı** sonucu vermeli.

**Tick bariyeri:** Ana döngü, controller ve spawner thread'leri o tick'teki işini bitirip yeniden beklemeye geçmeden bir sonraki tick'e ilerlemez (`wait_for_workers()`, `scaled_sleep()` içindeki uyanma hedefi kaydı). Önceden bir doğuş, CPU yükü altında tick sınırının öbür tarafına düşüp kuyruk sayısını ±1 kaydırabiliyordu ve bu "kabul edilmiş istisna" olarak belgelenmişti. Bariyerle bu fark kalktı: `verify_determinism.py`'nin yük altındaki testi de birebir aynı sonucu verir.

**Doğuş noktası:** Araç, şeridin sabit doğuş noktasında ya da şeridin son aracı henüz oradan ayrılmadıysa onun arkasında doğar (`Vehicle.place_at_spawn()`, ilk `move()` çağrısında ana döngüde). Önceki sürümde doğuş noktası her doğuşta geriye itiliyor ve hiç geri gelmiyordu. Uzun koşularda araçlar kavşaktan binlerce piksel uzakta doğuyor, talep fiilen seyreliyordu. 120 saniyelik koşularda etkisi küçüktü, 20 dakikalık koşuda doğuş mesafesi 322 pikselden 4530 piksele çıkıyordu.

## Hareket modeli ve bu oturumda düzeltilen dönüş-kayması hatası

Araçlar sabit hızla hareket eder (`current_speed() = base_speed * playback_speed`) — ivme/yavaşlama/car-following fiziği yoktur. Bu, ışık algoritmalarını karşılaştırmak için yeterlidir ama "gerçekçi trafik fiziği" iddiası için bir basitleştirmedir.

**Bulunan ve düzeltilen hata:** Bir araç dönüş yapmadan önce, dönüş tetik noktasına (`turnTriggerPoints`) kadar tam `speed` kadar ilerliyordu. `playback_speed` yükseldiğinde (örn. 8x) bu adım büyüdüğü için araç tetik noktasını fazlasıyla aşıyor, dönüş oradan başladığı için **final pozisyon playback_speed'e bağlı olarak kayıyordu** (aynı senaryo/seed'de 1x'te ve 8x'te farklı bitiş noktası). Düzeltme: `Vehicle.clamped_step_to_trigger()` — adımı, tetik noktasını aşmayacak şekilde sınırlıyor. Düzeltmeden sonra aynı (senaryo, seed) 1x ve 8x'te **birebir aynı** final pozisyonu veriyor (ölçülmüş, doğrulanmış).

## Araç oluşturma sırası: bulunan ikinci hata (thread-safety)

`Vehicle.__init__` içinde araç, `self.image` (pygame yüzeyi, disk okuması gerektiren `load_vehicle_image()` ile set edilir) atanmadan **önce** paylaşılan `engine.vehicles[direction][lane]` listesine ekleniyordu. Bu, controller thread'i tam bu dar pencerede (`append` ile `self.image` ataması arası) o araca `.image` üzerinden erişirse `AttributeError` ile çökmesine yol açıyordu — `optimal_ground_truth_strategy.py`'nin emergency-araç ETA hesaplaması (`vehicle.image.get_rect()` kullanıyor) bu şekilde çökebiliyordu, özellikle yoğun/uzun koşularda. Düzeltme: araç tam olarak hazırlandıktan (image dahil) **sonra** listeye eklenir — klasik "yalnızca tam kurulmuş nesneyi paylaş" deseni.

## Sinyal fazı yaşam döngüsü

`AdaptiveSignalController` (adaptif modda) veya `FixedTimeController` (sabit modda) hangi yönün ne kadar yeşil alacağına karar verir. Adaptif modda gerçek karar, `strategy.choose_next_phase(state, params, engine)`'e delege edilir (bkz. `docs/strategy_structure.md`). Faz geçişleri: yeşil → sarı (`yellow_time`) → bir sonraki yönün yeşili.

## Metrik toplama

`update_queue_metrics()` her tick'te bir kez çağrılır ve o anki kuyruk uzunluğunu örnekler (`queue_samples`). `Vehicle.update_signal_wait_time()` ise bir araç sinyal yüzünden bekliyorken her tick `self.waitTime`'a **gerçek simüle-saniye** (`current_simulation_delta`) ekler — bu, wait-time tabanlı metrikleri playback_speed'den bağımsız ve güvenilir kılar. Detaylı metrik tanımları için `docs/metrics_definitions.md`.

## Headless çalıştırma

`SimulationEngine(..., headless=True)` render yapmadan (pygame ekranı olmadan) aynı mantığı çalıştırır — `tools/run_batch_tests.py`'in tüm batch koşuları bunu kullanır. Determinizm garantisi headless ve render'lı modda aynıdır (aynı tick/saat mekanizması).

## Bilinen sınırlamalar (bu oturumda tespit edilen, henüz değişmeyen)

- `queue_length_average`/`queue_length_peak`, tick başına ağırlıksız örnekleniyor; `playback_speed` arttıkça örnekleme çözünürlüğü kabalaşır (daha az, daha büyük-aralıklı örnek). Aynı batch içinde tüm koşular aynı `playback_speed` kullandığı sürece (ki `tools/run_batch_tests.py` böyle yapıyor) karşılaştırmalar adil kalır; farklı `playback_speed`'lerde alınan mutlak sayılar doğrudan karşılaştırılmamalı.
- Tek kavşak modeli — koridor/ağ senkronizasyonu test edilemez.
- Yaya fazı modellenmiyor; `min_green` değerleri (5s) bu nedenle gerçek kentsel kavşaklara göre iyimser.
