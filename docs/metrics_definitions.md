# Metrik Tanımları

Her koşunun sonucuna yazılan metrikler burada tanımlanır. Hesap `simulation/engine.py` içindeki `collect_results()` ve `simulation/metrics.py` içindeki `summarize_direction()` ile yapılır.

Tek bir metrik yeterli değildir. Düşük ortalama bekleme, çok uzun bekleyen tek tek araçlarla birlikte görülebilir. Değerlendirme birden fazla metrik grubuyla yapılır.

## 1. Bekleme (wait) metrikleri

Bir aracın bekleme süresi (`waitTime`), araç sinyal yüzünden dururken her adımda simülasyon saniyesi cinsinden birikir (`Vehicle.update_signal_wait_time`). Oynatma hızından bağımsızdır.

| Metrik | Tanım |
|---|---|
| `overall_avg_wait` | Kesişimi geçen tüm araçların ortalama bekleme süresi |
| `overall_median_wait` (`overall_wait_p50`) | Ortanca bekleme. Uç değerlerden az etkilenir |
| `overall_max_wait` | Tek bir aracın gördüğü en uzun bekleme. Yüksek değer bir yönün ihmal edildiğine işaret eder |
| `overall_wait_p90` / `p95` / `p99` | En çok bekleyen %10, %5 ve %1'lik dilimin beklemesi |

Önemli kapsam notu: Bu metrikler yalnızca geçen (crossed) araçları kapsar. Koşu bittiğinde hâlâ kuyrukta olan araçlar bu ortalamaya girmez. Talebin kapasiteyi aştığı senaryolarda bu, `overall_avg_wait`'i olduğundan iyi gösterir. Bu yüzden aşağıdaki tamamlayıcı metrikler birlikte okunmalıdır.

### Isınma süresi, gecikme ve geçemeyen araçlar

| Metrik / ayar | Tanım |
|---|---|
| `warmup_time` (ayar) | Bu süreden önce doğan araçlar hiçbir istatistiğe girmez, kuyruk örneklemesi de bu süreden sonra başlar. Varsayılan 0. Kavşak boşken başlayan koşunun ilk dakikaları kalıcı durumu temsil etmediği için kullanılır |
| `overall_avg_delay` / `overall_delay_p95` | Kontrol gecikmesi: aracın dur çizgisini geçtiği an eksi doğduğu an eksi aynı mesafeyi serbest sürüşle alacağı süre. Kırmızıda durmanın yanında kuyrukta yavaş ilerlemeyi de içerir |
| `vehicles_measured` | Isınmadan sonra doğan, ölçüme giren araç sayısı |
| `vehicles_uncrossed` | Bunlardan koşu bittiğinde hâlâ kavşağı geçememiş olanlar |
| `uncrossed_avg_wait` | Geçemeyen araçların koşu sonuna kadar biriken ortalama beklemesi |

`tools/baseline_sweep_report.py` iki grubu birleştirerek tüm ölçülen araçların ortalama beklemesini raporlar: `(overall_avg_wait × geçen + uncrossed_avg_wait × geçemeyen) / vehicles_measured`. Geçemeyen araçların beklemesi koşu sonunda kesildiği için bu değer doygun senaryolarda hâlâ alt sınırdır.

## 2. Kuyruk (queue) metrikleri

| Metrik | Tanım |
|---|---|
| `queue_length_average` | Simülasyon boyunca her tick'te örneklenen kuyruk uzunluğunun ortalaması |
| `queue_length_peak` | Gözlenen en yüksek kuyruk uzunluğu |

Ne sayılıyor: Kuyruk uzunluğu, o yönde henüz kavşağı geçmemiş tüm araçların sayısıdır. Duran araçların yanında kavşağa yaklaşmakta olanları da içerir, yani dar anlamda "bekleyen kuyruk" değil "yaklaşımdaki araç sayısı"dır.

Örnekleme notu: kuyruk her adımda bir kez, ağırlıksız örneklenir. Oynatma hızı arttıkça bir adım daha uzun bir süreyi temsil eder ve kısa süreli sıçramalar kaçabilir. Tarama koşularının hepsi aynı oynatma hızını kullanır, bu yüzden birbirleriyle karşılaştırılabilir. Farklı oynatma hızlarında alınan mutlak değerler karşılaştırılmaz.

## 3. Geçen araç metrikleri

| Metrik | Tanım |
|---|---|
| `total_crossed` | Simülasyon boyunca kesişimi geçen toplam araç sayısı |
| `normal_vehicle_crossed` / `emergency_crossed` | Aynı sayının olağan araç ve acil durum aracı olarak ayrımı |

## 4. Acil durum aracı metrikleri

| Metrik | Tanım |
|---|---|
| `emergency_spawned` | Doğan acil durum aracı sayısı |
| `emergency_crossed` | Geçen acil durum aracı sayısı |
| `emergency_avg_wait` / `emergency_max_wait` | Acil durum araçlarının ortalama ve en uzun beklemesi |
| `emergency_wait_p95` / `p99` | Acil durum araçlarında en çok bekleyen %5 ve %1'lik dilimin beklemesi |
| `emergency_hold_count` / `emergency_total_hold_time` / `emergency_hold_max_time` | Yanan bir yeşilin, o yöndeki acil durum aracını geçirmek için kaç kez, toplam ne kadar ve tek seferde en fazla ne kadar uzatıldığı |
| `emergency_hold_success_count` | Uzatma alan acil durum araçlarından kaçının kavşağı geçtiği |
| `priority_activation_count` | Bir yeşilin acil durum önceliğiyle verildiği ya da yanan yeşilin bu yüzden kesildiği olay sayısı |

Bekleme metriklerindeki "yalnızca geçenler" kısıtı acil durum metrikleri için de geçerlidir. Sabit süreli kontrolde uzatma ve öncelik sayıları 0 kalır, çünkü acil durum aracına özel bir işlem yapılmaz.

## 5. Yön bazlı (per-direction) metrikler

Her yön (`right`, `down`, `left`, `up`) için ayrıca `avg_wait`, `median_wait`, `max_wait`, `crossed`, `queue_length_average`, `queue_length_peak` ve `wait_p90` / `p95` / `p99` hesaplanır. Bir kontrolcünün belirli bir yönü sürekli ihmal edip etmediği buradan görülür.
