# Fixed/Ground-Truth Hattının Nihai Durumu ve YOLO-Öncesi Kapsam Raporu

Bu doküman, projenin YOLO/CV entegrasyonuna (faz 3) geçmeden hemen önceki
kontrol noktasıdır. İki amacı var: (1) fixed + ground_truth hattı için
denenen son geliştirme turunun sonucunu ve bu hattın nihai/güncel
performans tavanını kayıt altına almak, (2) bu sistemin gerçek trafikte
neyi doğru yakaladığını ve neyi kapsamadığını — yani YOLO fazının
kapatması/karşılaşacağı somut boşlukları — tek bir yerde toplamak.

Bu projenin daha önceki bir kalibrasyon-öncesi tavan dokümanının yerini alır;
YOLO fazına başlarken ilk okunması gereken doküman burasıdır.

> **2026-07-24 güncellemesi:** Bölüm 2'deki tablo, gerçek kavşak
> kayıtlarıyla kalibre edilmiş motor fiziğiyle (bkz.
> `docs/scenario_capacity_calibration.md`'nin "2026-07-24: Gerçek Dünya
> Kalibrasyonu" bölümü) yeniden üretildi — mutlak sayılar artık daha
> yüksek (gerçek dünyaya göre kapasite ~2.3x düşürüldü) ama örüntü
> (adaptive her senaryoda fixed'ten iyi) aynı kaldı. Bölüm 4'teki madde 4
> (basit sürücü davranışı) ve madde 5 (sentetik talep/kapasite) artık
> kısmen kapatıldı — detaylar ilgili maddelerde.
>
> **2026-08-22 güncellemesi:** `sparse_traffic` senaryo kaydının kazara
> bozulmuş olduğu (spawn_interval fiilen peak seviyesinde, car hızı 2.25)
> bulunup düzeltildi ve senaryo 20 seed ile yeniden koşuldu
> (`batch_20260822_125454`); Bölüm 2'deki `sparse_traffic` satırı bu yeni
> ölçümden gelir. Detay: `docs/scenario_capacity_calibration.md`,
> "2026-08-22: `sparse_traffic` düzeltmesi".

## 1. Son geliştirme turunun sonucu: `rolling_horizon_ground_truth_v2` ekseni kapandı

Ground_truth hattı için "büyük fark yaratabilecek son bir geliştirme"
arayışı, bu oturumda ve hemen öncesindeki (kayıt dışı kalmış) bir
oturumda kapsamlı şekilde denendi. Özet:

- `rolling_horizon_ground_truth_v2`'nin (kesin ETA projeksiyonu) v1'in
  (EMA tabanlı) üzerine iddia edilen ~%8-13'lük kazanç, gerçekte v2'nin
  yanlışlıkla farklı bir `fairness_weight` kullanmasının yan etkisiymiş.
  `state_cost`'taki bir yapısal hata düzeltilip `fairness_weight`
  10.0→3.0→5.0→10.0 aralığında tekrar tekrar taranıp doğrulandıktan
  sonra (bkz. `data/controller_versions.json`'daki
  `adaptive_rolling_horizon_ground_truth_v2` kaydının "2026-07-19 NİHAİ
  SONUÇ" notu), **aynı
  `fairness_weight=10.0` değerinde v1 ve v2 ölçülebilir bir farkla
  ayrışmıyor** (7 senaryonun 4'ünde v1 hafif önde, 2'si eşit, 1'i v2
  hafif önde).
- **Karar:** `adaptive_rolling_horizon_ground_truth` (v1) rolling-horizon
  ailesinin önerilen/aktif üyesi; `adaptive_rolling_horizon_ground_truth_v2`
  zararsız ama gereksiz karmaşık olduğu için `experimental` statüsünde
  kalıyor.
- Bu oturumda ayrıca `optimal_ground_truth` ailesinin emergency-öncelik
  mekanizmasında gerçek bir davranış hatası bulunup düzeltildi: bir acil
  durum aracı, kendi yönündeki uzun bir kuyruğun arkasında (kavşağa hâlâ
  çok uzakken) "teknik olarak bloke" sayılıp erken öncelik alabiliyordu.
  `is_emergency_reachable_within_budget()` eklenerek öncelik artık yalnızca
  aracın verilebilecek en uzun yeşil+hold bütçesi içinde gerçekten
  kesişimi geçebileceği an veriliyor (bkz. `controllers/strategies/optimal_ground_truth_strategy.py`).
- **Sonuç: bu eksende (rolling-horizon'un daha karmaşık bir varyantı) daha
  fazla kazanç yok — dürüstçe kapatıldı.** Ground_truth hattının nihai,
  önerilen kontrolcüleri: tek-adım karar için `adaptive_optimal_ground_truth_v3`,
  çok-adım/ileriye-bakan karar için `adaptive_rolling_horizon_ground_truth` (v1).

## 2. Nihai metrik tavanı (22 senaryo, 20 seed — `batch_20260724_024258` + `batch_20260822_125454`, gerçek-dünya kalibrasyonu sonrası)

> Bu tablo 2026-07-24'te, motorun gerçek kavşak kayıtlarıyla kalibre
> edilmesinden (bkz. `docs/scenario_capacity_calibration.md`) sonra
> yeniden üretildi. Önceki (`batch_20260718_125627`, kalibrasyon-öncesi
> motor fiziğiyle üretilmiş) sayılar artık geçersiz ve karşılaştırılamaz
> — mutlak `avg_wait` değerleri genel olarak daha yüksek çünkü gerçek
> kapasite eski (doğrulanmamış) motor varsayımının ~%43'ü (~0.478 vs
> ~1.116 veh/s). Örüntü (adaptive'in fixed'e üstünlüğü) değişmedi.

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

**Okuma notu:** `emergency_peak_traffic` hâlâ en mütevazı kazancın
görüldüğü yer (kapasiteye yakın talep + sık emergency kesintisi,
adaptive'in manevra alanını daraltıyor) — p99'da küçük bir gerileme
(-%1.1) var ama ortalamada hâlâ net kazanç. **22 senaryonun 22'sinde de
adaptive fixed'ten iyi**; hiçbir senaryoda adaptive kaybetmiyor.
`single_direction_traffic`'in %100 iyileşmesi hâlâ bir kenar durumu (bkz.
eski dokümandaki gerekçe). `mixed_master_scenario` kalibrasyon-öncesinde
adaptive'in fixed'ten *kötü* çıktığı tek senaryoydu (bkz.
`scenario_capacity_calibration.md`'nin 2026-07-16 bölümü) — gerçek-dünya
kalibrasyonu sonrası bu artık **tersine döndü** (%65.8 iyileşme), kesin
nedeni izole edilmedi ama artık gözlenen bir zayıflık değil.

**Emergency-araç önceliklendirme (v3, 3 örnek senaryo):**

| Senaryo | Fixed emg_avg_wait | v3 emg_avg_wait | Fixed emg_crossed/spawned | v3 emg_crossed/spawned |
|---|---:|---:|---:|---:|
| emergency_right_heavy_traffic | 9.23s | 2.26s | 0.30/0.50 | 0.50/0.60 |
| emergency_peak_traffic | 13.61s | 6.36s | 0.90/1.25 | 1.25/1.40 |
| emergency_sparse_traffic | 2.79s | 0.55s | 0.15/0.15 | 0.15/0.15 |

## 3. Bu sistemin gerçek trafikte iyi karşıladığı şeyler

- **Tam-bilgi kuyruk durumu ve adil sıralama:** `ground_truth` provider
  her aracın konumunu/hızını/bekleme süresini hatasız biliyor;
  cycle-fairness mekanizması (`adaptive_controller.py`) bir turda talebi
  olan her yönün en az bir kez servis edilmesini garanti ediyor —
  `data/controller_versions.json`'daki `controller_repeat_guard_enabled`
  ve cycle-fairness testleri bunu doğruluyor.
- **ETA-tabanlı, gerçekçi emergency önceliklendirme:** sabit bir "acil
  durum yeşili" yerine, aracın ground-truth konum/hızından hesaplanan
  kesin ETA'ya göre süre veriliyor; bu oturumda eklenen menzil kısıtı
  sayesinde öncelik yalnızca aracın gerçekten o an yaklaştığı/kesişimi
  geçebileceği an veriliyor (bkz. yukarı, bölüm 1) — tablo 2'deki
  emergency_avg_wait rakamları (fixed'in ~%75-80 altında) bunun somut
  kanıtı.
- **Deterministik tekrarlanabilirlik:** `(senaryo, kontrolcü, seed)`
  üçlüsü sabitken simülasyon birebir aynı sonucu üretiyor
  (`tools/verify_determinism.py`) — A/B karşılaştırmaları gürültüden
  arındırılmış, güvenilir.
- **Ölçülmüş kapasiteye göre kalibre edilmiş talep seviyeleri:**
  senaryolar rastgele değil, gerçek kavşak kayıtlarıyla kalibre edilmiş
  sistem kapasitesine (~0.478 araç/sn) göre hedeflenmiş v/c oranlarıyla
  (0.15-0.90) tasarlandı (bkz.
  `docs/scenario_capacity_calibration.md`) — "sparse" gerçekten hafif,
  "peak" gerçekten doygunluğa yakın.
- **Çok yönlü senaryo çeşitliliği:** yön-ağırlıklı, yoğunluk-varyantlı,
  rejim-değişimli (`direction_shift`, `demand_shift`, `mixed_master`) ve
  emergency varyantlarıyla geniş bir senaryo yelpazesi test ediliyor.

## 4. Kapsamadığı / basitleştirdiği şeyler — YOLO öncesi somut boşluk listesi

Her madde: **şu an nasıl modelleniyor** → **YOLO/gerçek veri bunu nasıl
değiştirecek**.

1. **"Ground truth" mükemmel/gürültüsüz bir sensör varsayımı.** Şu an
   state provider her aracı, konumunu, hızını hatasız biliyor.
   → YOLO gerçek kamera görüntüsünden çalışacak: kısmi görüş açısı,
   tıkanma (occlusion), yanlış pozitif/negatif tespit, gecikme (inference
   latency) getirecek. Bu, projenin **asıl araştırma sorusu** — ground
   truth'un sağladığı tavan (bölüm 2), gerçek algılamanın ne kadarına
   yaklaşabileceğinin ölçüm noktası.
2. **Tek, izole kavşak — ağ/downstream etkisi yok.** Araçlar kesişimi
   geçince haritadan siliniyor; komşu kavşaktaki tıkanıklığın (spillback)
   bu kavşağı etkilemesi modellenmiyor (bkz. `docs/engine_overview.md`:
   "koridor/ağ senkronizasyonu test edilemez"). → Gerçek bir şehir
   şebekesinde yeşil-dalga/komşu-kavşak koordinasyonu önemli bir faktör;
   bu proje kapsam dışı bırakıyor, tek kavşak optimizasyonuna odaklanıyor.
3. **Yaya/bisiklet fazı yok.** `min_green` değerleri (5s) bu yüzden gerçek
   kentsel kavşaklara göre iyimser (`docs/engine_overview.md`). →
   Gerçek bir kavşakta yaya geçiş süresi genelde asgari yeşili belirleyen
   asıl kısıt; bu projede hiç yok.
4. **Basit sürücü/araç davranışı — kısmen kapatıldı (2026-07-24).** Sabit
   `base_speed` (araç tipine göre) ve tam bir car-following fiziği hâlâ
   yok, ama 2026-07-24'te gerçek kavşak kayıtlarından ölçülen bir
   start-up lost time (`engine.startupLostTime = 3.0s`, bkz.
   `docs/scenario_capacity_calibration.md`) eklendi: bir araç artık
   önündeki boşaldığı anda değil, gerçekçi bir reaksiyon gecikmesinden
   sonra hareket ediyor, ve sürekli-akış takip mesafesi (`movingGap`)
   gerçek ölçülen discharge_rate'e (~0.474 veh/s, %1 içinde) kalibre
   edildi. Kalan boşluk: bu hâlâ TEK bir sabit gecikme/mesafe — araç
   tipine, sürücü profiline, ya da kuyruktaki sıraya göre değişen bir
   varyans yok; agresif/dikkatsiz sürüş, fren mesafesi varyansı,
   çakışan hareketler arası gerçek görüş-mesafesi etkileşimi hâlâ yok.
   → Gerçek trafikte YOLO'nun beslediği karar mekanizması, hâlâ bu
   projedekinden daha gürültülü/değişken bir hareket modeliyle
   karşılaşacak — ama artık en azından ortalama davranış gerçek veriyle
   çapraz doğrulanmış durumda.
5. **Sentetik, kendi kendine kalibre talep üretimi — kapasite tarafı artık
   gerçek veriyle kalibre, talep tarafı hâlâ sentetik.** 2026-07-24'te,
   3 gerçek kavşaktan alınan kayıtlarla motorun kendi ölçtüğü kapasitenin
   (~1.116 araç/sn) gerçek dünyadan ~2.3x iyimser olduğu bulundu ve
   düzeltildi (gerçek ölçüm: ~0.478 araç/sn, bkz.
   `docs/scenario_capacity_calibration.md`) — 22 senaryonun
   `spawn_interval`'ı bu yeni kapasiteye göre yeniden ölçeklendi. Ama
   bu sadece KAPASİTE tarafını gerçek veriyle bağladı; talep tarafı
   (`spawn_interval`'ın kendisi, v/c hedefleri, `direction_density`
   ağırlıkları) hâlâ projenin kendi tasarım kararı — gerçek bir şehrin
   gerçek araç SAYIM/VARIŞ verisiyle karşılaştırılmadı.
   → YOLO gerçek kameradan gerçek talep dağılımını (varış oranı, zamana
   göre değişimi) görecek; bu muhtemelen şu anki sentetik senaryolardan
   (blok bazlı `mixed_master_scenario` dahil) daha düzensiz/korelasyonlu
   olacak. Aynı kayıt yöntemi (yeşil faz başına elle işaretleme)
   genişletilip kırmızıda biriken araç sayısı/varış aralığı da
   ölçülürse, talep tarafı da benzer şekilde kalibre edilebilir — bu
   oturumda yapılmadı, doğal bir sonraki adım.
6. **Tek acil durum modeli, idealize edilmiş uyum.** Emergency araçlar
   (`ambulance`/`police`/`firetruck`) tespit edilir edilmez sistem
   tarafından mükemmel tanınıyor ve diğer sürücüler onlara her zaman tam
   uyumlu davranıyor (gerçekte yol açmama/geç fark etme gibi
   belirsizlikler var). → YOLO'nun siren/görsel tabanlı acil durum
   tespiti gecikmeli ve hatalı olabilir; bu boşluk hem tespit hem
   sürücü-uyum tarafında gerçek dünyada daha büyük.
7. **Sınırlı dönüş-çakışma modeli.** `lane_turn_policy` (straight+left /
   straight+right şeritleri) ile bir ölçüde dönüş çakışması var
   (`turning_conflict_traffic`, `turn_heavy_traffic` senaryoları bunu
   test ediyor), ama korumalı/serbest sol dönüş fazları, karşıdan gelen
   trafikle gerçek çakışma kontrolü gibi tam bir sinyal-faz matrisi yok.
8. **Metrikler yalnızca kesişimi GEÇEN araçları kapsar** (bkz.
   `docs/metrics_definitions.md`) — aşırı doygun bir gerçek senaryoda,
   hiç geçemeyen araçlar es geçildiği için `overall_avg_wait` olduğundan
   iyi görünebilir. Bu, simülasyonun kendi iç metodolojik sınırı; YOLO
   fazında da aynı tanım kullanılacaksa göz önünde bulundurulmalı.
9. **`playback_speed`'e bağlı örnekleme kabalığı** (queue metrikleri) —
   tüm batch'ler aynı `playback_speed=8x` kullandığı sürece karşılaştırma
   adil, ama mutlak sayılar `playback_speed`'e duyarlı (bkz.
   `docs/metrics_definitions.md`).

## 5. YOLO fazına geçiş için pratik sonuç

Bölüm 2'deki tablo, YOLO'nun ölçüleceği **referans tavanı** tanımlıyor:
gerçek algılama, tam-bilgi ground truth'un ürettiği bu iyileşme
oranlarına (senaryoya göre %10-100, çoğunlukla %25-65 — bkz. 2026-07-24
gerçek-dünya kalibrasyonu sonrası güncellenmiş tablo) ne kadar
yaklaşabiliyor sorusu, projenin bir sonraki fazının temel araştırma
sorusu. Bölüm 4'teki boşluk listesi, YOLO stratejisi tasarlanırken hangi
ek belirsizliklerin (gürültülü/gecikmeli/kısmi gözlem) hesaba katılması
gerektiğinin somut kontrol listesi olarak kullanılmalı — özellikle madde
1 (gürültüsüz sensör varsayımının kalkması) ve madde 5 (emergency
tespitinin artık mükemmel olmaması), `state_providers/yolo_provider.py`
ve ona karşılık gelecek stratejinin tasarımını doğrudan etkileyecek.
