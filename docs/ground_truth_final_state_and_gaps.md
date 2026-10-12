# Fixed/Ground-Truth Hattının Nihai Durumu ve YOLO-Öncesi Kapsam Raporu

Bu doküman, projenin YOLO/CV entegrasyonuna (faz 3) geçmeden hemen önceki
kontrol noktasıdır. İki amacı var: (1) fixed + ground_truth hattı için
denenen son geliştirme turunun sonucunu ve bu hattın nihai/güncel
performans tavanını kayıt altına almak, (2) bu sistemin gerçek trafikte
neyi doğru yakaladığını ve neyi kapsamadığını — yani YOLO fazının
kapatması/karşılaşacağı somut boşlukları — tek bir yerde toplamak.

Bu projenin daha önceki bir kalibrasyon-öncesi tavan dokümanının yerini alır;
YOLO fazının bu tavana göre sonucu Bölüm 5'te.

> **2026-10-12 güncellemesi:** Bölüm 2 yeni ölçüm yöntemiyle baştan
> yazıldı ve aşağıdaki iki eski güncelleme notunun anlattığı tablonun
> yerini aldı. Bu belgenin başka yerlerinde eski tabloya dayanan
> ifadeler ("her senaryoda adaptif önde" gibi) Bölüm 2 ile çelişirse
> Bölüm 2 geçerlidir.
>
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
arayışı kapsamlı şekilde denendi. Özet:

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
- Aynı turda `optimal_ground_truth` ailesinin emergency-öncelik
  mekanizmasında gerçek bir davranış hatası bulunup düzeltildi: bir acil
  durum aracı, kendi yönündeki uzun bir kuyruğun arkasında (kavşağa hâlâ
  çok uzakken) "teknik olarak bloke" sayılıp erken öncelik alabiliyordu.
  `is_emergency_reachable_within_budget()` eklenerek öncelik artık yalnızca
  aracın verilebilecek en uzun yeşil+hold bütçesi içinde gerçekten
  kesişimi geçebileceği an veriliyor (bkz. `controllers/strategies/optimal_ground_truth_strategy.py`).
- **Sonuç: bu eksende (rolling-horizon'un daha karmaşık bir varyantı) daha
  fazla kazanç yok, eksen kapatıldı.** Ground_truth hattının nihai,
  önerilen kontrolcüleri: tek-adım karar için `adaptive_optimal_ground_truth_v3`,
  çok-adım/ileriye-bakan karar için `adaptive_rolling_horizon_ground_truth` (v1).

## 2. Güncel sonuçlar (22 senaryo, 2026-10-12 taraması)

> **Bu bölüm 2026-10-12'de baştan yazıldı.** Önceki tablo (`batch_20260724_024258`)
> üç nedenle geçersiz: (1) üretildiği kod sürümü kayıtlı değil ve bugünkü kodla
> yeniden üretilemiyor, (2) 120 saniyelik koşular kavşak boşken başlayan geçiş
> dönemini ölçüyordu ve geçemeyen araçları saymıyordu, (3) doğuş noktası hatası
> (bkz. `docs/engine_overview.md`) uzun koşularda talebi seyreltiyordu. Eski
> tablodaki "22 senaryonun 22'sinde adaptif önde" sonucu artık geçerli değildir.

**Yöntem** (`tools/baseline_sweep.py`, rapor `tools/baseline_sweep_report.py`):

- Koşu 600 sn, ilk 120 sn ısınma. `mixed_master_scenario` kendi 1800 sn süresiyle.
- Senaryo başına 10 seed (`mixed_master_scenario` 3), toplam 1491 koşu.
- Sabit süre tek bir değerle değil 5, 6, 8, 10 ve 12 sn yeşil süreleriyle tarandı. Adaptif kontrolcü her senaryonun **en iyi** sabit süresiyle karşılaştırılır.
- Bekleme, ölçüme giren tüm araçları kapsar: geçenler ve koşu sonunda hâlâ kuyrukta olanlar (bkz. `docs/metrics_definitions.md`).
- Adaptif: `adaptive_optimal_ground_truth_v3` ve `adaptive_rolling_horizon_ground_truth` (v1).

**Özet**

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

**Okuma notları**

- **Kazanç trafiğin dengesizliğinden geliyor.** Yönlere eşit dağılmayan ya da seyrek trafikte (tek yönlü, aşırı yönlü, sağ/dikey ağırlıklı, seyrek, boş kavşak) kazanç %42-100 ve her koşuda tekrarlanıyor. Sabit süre boş ya da az yüklü yöne yeşil yakmaya devam ediyor.
- **Dengeli trafikte fark küçük.** Dengeli, dönüş ağırlıklı, yön/talep kaymalı, patlamalı ve dönüşümlü senaryolarda iyi ayarlanmış 6 sn'lik sabit süreye göre kazanç %1-11, koşuların bir kısmında sabit süre önde. Nedeni `docs/strategy_structure.md`'de: v3 yeşil süresini pratikte değiştirmiyor.
- **Doygunlukta adaptif geride.** `peak_traffic` ve `emergency_peak_traffic`'te talep kapasitenin üstünde, araçların yaklaşık beşte biri koşu sonunda hâlâ kuyrukta. Adaptif burada %8 geride. Kapasite yetmediğinde sıralama bir şey kazandırmıyor.
- **Varsayılan sabit süre (10 sn) kötü bir referans.** 22 senaryonun 18'inde en iyi sabit süre 6 sn. "Sabit 10 sn'ye göre kazanç" sütunu bu yüzden adaptifi olduğundan iyi gösterir.
- `single_direction_traffic`'teki %100 bir kenar durumudur: tek aktif yön sürekli yeşil alır.

### Acil durum araçları

Acil durum araçlarının ortalama beklemesi (sn, kavşağı geçenler):

| Senaryo | sabit 6s | v3 | rolling horizon | yeşil uzatması (v3, 10 koşu toplamı) |
|---|---:|---:|---:|---:|
| emergency_balanced_traffic | 27.7 | 3.4 | 2.6 | 39 |
| emergency_right_heavy_traffic | 44.5 | 3.0 | 2.7 | 27 |
| emergency_peak_traffic | 43.9 | 9.6 | 21.9 | 155 |
| emergency_sparse_traffic | 12.7 | 0.6 | 0.6 | 4 |
| emergency_low_frequency_mixed_traffic | 14.7 | 1.6 | 2.0 | 7 |

Adaptif kontrolcülerin en net üstünlüğü burada: acil durum aracı sabit sürede 13-45 sn beklerken öncelikli kontrolde 10 sn'nin altında bekliyor. Tek istisna doygun `emergency_peak_traffic`'te rolling horizon (22 sn). Bu tablo, yeşil uzatması düzeltildikten sonraki ilk ölçümdür.

## 3. Bu sistemin gerçek trafikte iyi karşıladığı şeyler

- **Tam-bilgi kuyruk durumu ve adil sıralama:** `ground_truth` provider
  her aracın konumunu/hızını/bekleme süresini hatasız biliyor;
  cycle-fairness mekanizması (`adaptive_controller.py`) bir turda talebi
  olan her yönün en az bir kez servis edilmesini garanti ediyor —
  `data/controller_versions.json`'daki `controller_repeat_guard_enabled`
  ve cycle-fairness testleri bunu doğruluyor.
- **ETA-tabanlı, gerçekçi emergency önceliklendirme:** sabit bir "acil
  durum yeşili" yerine, aracın ground-truth konum/hızından hesaplanan
  kesin ETA'ya göre süre veriliyor; sonradan eklenen menzil kısıtı
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
   ölçülürse, talep tarafı da benzer şekilde kalibre edilebilir. Bu
   yapılmadı, doğal bir sonraki adım.
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

## 5. YOLO fazının sonucu

Bu doküman YOLO fazından önce yazıldı. Faz tamamlandı: kameralı kontrolcü
(`adaptive_camera_queue_v1`) Bölüm 2'deki tavana ortanca 1,2 sn ek beklemeyle
yaklaşıyor, en yüksek fark 5,6 sn. Tam tablo `reports/camera/summary.md`'de.

Bölüm 4'teki boşluklardan hangileri ölçüldü:

- **Madde 1 (kısmi görüş açısı):** ölçüldü. Kontrolcü yalnızca 900x900 kareyi
  görüyor, kare dışındaki kuyruk sayılmıyor.
- **Madde 5 (acil durum tespiti):** kısmen ölçüldü. Araç sınıfı görüntüden
  tespit ediliyor, kare dışında bekleyen araç görülmüyor. Bekleme v3'te
  0,6-9,6 sn, kamerada 1,3-35,0 sn.
- **Tespit hataları, ışık, hava, örtüşme:** ölçülmedi. Görüntüler simülasyonun
  kendi çizimi olduğu için model neredeyse hatasız (mAP50-95 0,98). Gerçek
  kamera görüntüsüyle bu maliyet ayrıca ölçülmeli.
