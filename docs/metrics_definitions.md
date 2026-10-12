# Metrik Tanımları

Bu doküman, `simulation/engine.py`'nin `collect_results()` metodunda hesaplanıp her deney sonucuna (`data/batches/*.jsonl`, batch raporları) yazılan metrikleri tanımlar. Kaynak: `simulation/metrics.py` (`summarize_direction`) ve `engine.py`'deki `collect_results`.

Tek bir metrik yeterli değildir — düşük ortalama bekleme, yüksek `max_wait` (starvation) ile birlikte gelebilir. Değerlendirme her zaman birden fazla metrik grubuyla birlikte yapılmalı.

## 1. Bekleme (wait) metrikleri

Bir aracın `waitTime`'ı, sinyal kırmızıyken duruyorken tick başına **gerçek simüle-saniye** (`current_simulation_delta`) eklenerek birikir (`Vehicle.update_signal_wait_time`) — bu nedenle `playback_speed`'den bağımsız, güvenilir bir ölçümdür.

| Metrik | Tanım |
|---|---|
| `overall_avg_wait` | Kesişimi geçen tüm araçların ortalama bekleme süresi |
| `overall_median_wait` (`overall_wait_p50`) | Medyan bekleme — uç değerlerden daha az etkilenir, "tipik" davranışı gösterir |
| `overall_max_wait` | Tek bir aracın gördüğü en yüksek bekleme — yüksekse starvation/adalet sorununa işaret eder |
| `overall_wait_p90` / `p95` / `p99` | Kuyruk (tail latency) davranışı — "en kötü %10/%5/%1'lik dilim ne kadar bekliyor" |

**Önemli kapsam notu:** Bu metrikler yalnızca **geçen** (crossed) araçları kapsar — hâlâ kuyrukta bekleyen araçlar (simülasyon bitene kadar geçemeyenler) bu ortalamaya dahil edilmez. Aşırı doygun bir senaryoda (talep kapasiteyi aştığında) bu durum `overall_avg_wait`'i gerçekte olduğundan **daha iyi gösterebilir** — çünkü en çok mağdur olan araçlar (hiç geçemeyenler) hesaba katılmıyor.

## 2. Kuyruk (queue) metrikleri

| Metrik | Tanım |
|---|---|
| `queue_length_average` | Simülasyon boyunca her tick'te örneklenen kuyruk uzunluğunun ortalaması |
| `queue_length_peak` | Gözlenen en yüksek kuyruk uzunluğu |

**Bilinen metodolojik not:** `update_queue_metrics()` her tick'te bir örnek alır (ağırlıksız). `playback_speed` arttıkça bir tick daha fazla simüle-saniyeyi temsil eder, yani örnekleme çözünürlüğü kabalaşır — ani/kısa süreli sıçramalar yüksek `playback_speed`'de kaçırılabilir. Aynı batch içindeki tüm koşular aynı `playback_speed` kullandığı sürece (bu projedeki tüm batch koşuları 8x kullanıyor) karşılaştırmalar birbirine göre adildir; farklı `playback_speed` değerlerinde alınmış mutlak sayılar doğrudan karşılaştırılmamalıdır.

## 3. Throughput metrikleri

| Metrik | Tanım |
|---|---|
| `total_crossed` | Simülasyon boyunca kesişimi geçen toplam araç sayısı |
| `normal_vehicle_crossed` / `emergency_crossed` | Aynı sayının normal/emergency araç kırılımı |

## 4. Emergency-araç metrikleri

| Metrik | Tanım |
|---|---|
| `emergency_spawned` | Doğan emergency araç sayısı |
| `emergency_crossed` | Geçen emergency araç sayısı |
| `emergency_avg_wait` / `emergency_max_wait` | Emergency araçların ortalama/maksimum bekleme süresi |
| `emergency_wait_p95` / `p99` | Emergency araç bekleme kuyruğu |
| `emergency_hold_count` / `emergency_total_hold_time` / `emergency_hold_max_time` | Devam eden bir yeşilin, içindeki emergency aracı geçirmek için kaç kez / toplam ne kadar / tek seferde en fazla uzatıldığı (yalnızca hold mantığı olan stratejilerde dolu olur — `optimal_ground_truth`'ta `get_green_extension` hook'u bunu üretir). Muhasebesi `adaptive_controller.py`'nin `run_green_phase()`'inde, hook'un döndürdüğü `extension` değerinden jenerik olarak yapılır — herhangi bir strateji bu hook'u tanımlarsa otomatik çalışır. |
| `emergency_hold_success_count` | Hold alan emergency araçlardan kaç tanesinin gerçekten kesişimi geçtiği (`vehicle.receivedEmergencyHold` bayrağı üzerinden, `simulation/vehicle.py`'de aracın `crossed` olduğu anda sayılır) |
| `priority_activation_count` | Bir fazın (ilk seçim veya mid-phase preemption) emergency önceliği yüzünden verildiği toplam olay sayısı. `choose_next_phase`'in döndürdüğü `decision_meta={"emergency_priority": True}` (normal faz seçimi) veya `should_preempt`'in `True` dönmesi (preemption) sayılır — strateji-bağımsız, `adaptive_controller.py`'de tutulur (bkz. `docs/strategy_structure.md`'deki `decision_meta` sözleşmesi). |

Bekleme metriklerindeki "yalnızca geçenler dahil" kısıtı emergency metrikleri için de geçerlidir. `emergency_priority_enabled=False` olan bir kontrolcü versiyonunda (bkz. `docs/strategy_structure.md`) bu beş metriğin tamamı yapısal olarak 0 kalır — emergency araçlar hiç özel muamele görmediği için ölçülecek bir hold/preemption/priority olayı olmaz; bu bir hata değil, switch'in beklenen sonucudur.

## 5. Yön bazlı (per-direction) metrikler

Her yön (`right`/`down`/`left`/`up`) için ayrıca `avg_wait`, `median_wait`, `max_wait`, `crossed`, `queue_length_average`, `queue_length_peak`, `wait_p90`/`p95`/`p99` hesaplanır (`summarize_direction`) — bir kontrolcünün belirli bir yönü sistemli şekilde ihmal edip etmediğini görmek için kullanılır.

## 6. `discharge_rate` (metrik değil, dahili kavram)

Metrik olarak dışarı raporlanmaz ama `optimal_ground_truth_strategy.py`'nin karar mantığının merkezinde yer alır: bir yön yeşilken, o fazda kaç aracın gerçekten geçtiğinin (`crossed` artışı / geçen yeşil süresi) EMA (üstel hareketli ortalama, α=0.35) ile öğrenilmiş hâli. "Kuyruğu gerçekten temizlemek için ne kadar yeşil gerekli" hesabının (`queue_count / discharge_rate`) girdisidir.
