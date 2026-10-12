# Strateji Yapısı (`controllers/strategies/`)

Bu klasör yalnızca 2 dosya içerir:

| Dosya | Rolü |
|---|---|
| `base_strategy.py` | Soyut sözleşme |
| `optimal_ground_truth_strategy.py` | `ground_truth`'un tek stratejisi |

## Sözleşme: `base_strategy.py`

```python
class BaseAdaptiveStrategy:
    strategy_key = "base"

    def choose_next_phase(self, state, params, engine):
        raise NotImplementedError
```

Bu, adaptif stratejinin uyması gereken tek soyut sözleşmedir: `state` (provider'dan gelen soyut trafik durumu — `{"right": N, "down": N, ...}`), `params` (o kontrolcü versiyonunun ayarlanabilir parametreleri) ve `engine`'i alır; `(direction, green_time, reason, decision_meta)` döndürür. `decision_meta` bir dict'tir, en az `{"emergency_priority": bool}` içerir — `adaptive_controller.py` bunu, strateji-özel karar mantığını bilmeden emergency metriklerini (`priority_activation_count`) doğru saymak için kullanır. `choose_phase()` geriye dönük uyumluluk için 3-tuple (meta'sız) dönen bir stratejiyi de kabul eder (`decision_meta={}` varsayılır). `controllers/adaptive_controller.py`'deki `AdaptiveSignalController`, hangi strateji sınıfının kullanılacağını `STRATEGY_MAP` (strategy_key → sınıf) üzerinden çözer; faz yaşam döngüsü, min/max green sınırları, emergency metrik muhasebesi gibi ortak mekanikleri kendisi yönetir, kararın içeriğini stratejiye bırakır. Yeni bir algoritma eklemek = yeni bir strateji sınıfı + `STRATEGY_MAP` girdisi + `data/controller_versions.json`'a bir kayıt; `adaptive_controller.py`'a dokunmadan.

## `optimal_ground_truth_strategy.py` — `ground_truth`'un tek stratejisi

Ground truth'un tam-bilgi avantajını (her aracın konumu, hızı, bekleme süresi bilinir) kuyruk teorisinden gelen az sayıda (~10) gerekçeli parametreyle kullanan bir karar mekanizması — sezgisel, elle-ayarlanmış onlarca ağırlık yerine. `data/controller_versions.json`'da bu stratejiyi kullanan üç kontrolcü versiyonu var: `adaptive_optimal_ground_truth` (v1, orijinal), `adaptive_optimal_ground_truth_v2` (bkz. aşağıda) ve `adaptive_optimal_ground_truth_v3` — aynı `strategy_key`, farklı `params`.

- **Yön seçimi:** `index[d] = queue_count[d] + λ * excess_wait[d]` — toplam beklemeyi minimize eden greedy-optimal kural + adalet kısıtının fiyatlandırması. Bir **cycle-fairness** katmanı bunu sınırlar: bir turda henüz servis edilmemiş aktif bir yön varsa, index'e göre kazanan zaten servis edilmişse unserved yönler arasından en yüksek index'e sahip olan seçilir. Bu işaretleme (`mark_cycle_served`), stratejinin kendi içinde değil, `adaptive_controller.py`'nin `select_and_prepare_phase()`'inde -- tüm override'lar (initial_selection, single_demand) çözüldükten sonra, kesinleşen yönle -- tek noktadan yapılır. Bu katman `params.cycle_fairness_enabled` (varsayılan `True`) ile tamamen kapatılabilir; kapalıyken yön seçimi saf `index[d]` en yükseğine göre yapılır, unserved yön garantisi devre dışı kalır.
- **Yeşil süresi:** `queue_count[d] / discharge_rate[d]` — "kuyruğu gerçekten temizlemek için ne kadar gerekiyor" (discharge_rate, geçmiş fazlardan EMA ile öğrenilir) — 2+ yön aktifken `multi_direction_max_green` tavanına clamp'lenir (bkz. aşağıdaki "clamp neden gevşetilmedi" notu). v3'te bu tavan artık sabit değil: `params.demand_share_scaling_exponent` (v1/v2'de 0 = kapalı) >0 iken, seçilen yönün aktif talep içindeki payına göre ölçekleniyor.
- **Emergency:** `params.emergency_priority_enabled` (varsayılan `True`) açıkken, ETA'ya dayalı **gerçek** mid-phase preemption (`should_preempt`) ve hold (`get_green_extension`) — sabit bir süre değil, ground truth'taki konum/hız verisinden hesaplanan kesin süre. **Kapalıyken** (`False`) emergency araçlar hiçbir özel muamele görmez: state zaten tip ayrımı yapmadan tüm araçları saydığından (`ground_truth_provider.get_state()`), emergency araçlar otomatik olarak normal kuyruk üyesi gibi işlenir — ekstra kod dalı gerekmez.
- **Açlık koruması (opsiyonel, değeri versiyona göre değişir):** `params.emergency_starvation_override_limit` verilmişse, emergency önceliği vermeden önce `other_direction_severely_starving()` başka bir yönün zaten kritik derecede aç olup olmadığını kontrol eder — kendi kuyruğuna sıkışıp yavaş ilerleyen bir emergency aracın her karar turunda aynı yönü kazanıp diğer tüm yönleri sınırsız aç bırakmasını engeller (`mixed_master_scenario` ile bulunup v1'de düzeltilen hata). v1'de bu değer 60s; v2'de 90s'ye gevşetildi — bir parametre taramasıyla bulundu: standart (kısa) senaryolarda hiç tetiklenmediği, ama `mixed_master_scenario` gibi çok uzun/sürekli senaryolarda normal trafiği v1 seviyesinde tuttuğu için seçildi. Parametre hiç verilmezse bu koruma tamamen devre dışı kalır (koşulsuz öncelik) — v2 ilk denemede bu şekilde test edildi ve `mixed_master_scenario`'da ciddi bir normal-trafik regresyonuna yol açtığı ölçüldü, bu yüzden nihai v2 koşulsuz değil, 90s limitli.

`optimal_ground_truth`, `ground_truth` provider'ının tam bilgi avantajını (kesin konum/hız) doğrudan kullandığı için **tasarım gereği** `yolo` ile uyumlu değildir — bu bir eksiklik değil, "ground_truth = tam bilgiyle ulaşılabilecek tavan" rolünün doğal sonucu.

## `adaptive_optimal_ground_truth_v2` ve `multi_direction_max_green` clamp'i neden gevşetilmedi

v2 üzerinde yapılan bir inceleme, batch verisinde `choose_next_phase`'in normal-trafik kararlarının **%95.7'sinde** `green_time`'ın `queue_count/discharge_rate` formülü yerine `multi_direction_max_green` clamp'inin kendisi tarafından belirlendiğini gösterdi (2+ aktif yön olduğunda). İlk hipotez, bu clamp'in formülü bastırdığı ve gevşetilmesinin (6 → 10/15/20) sonucu iyileştireceğiydi.

**Ölçüm bu hipotezi çürüttü.** `multi_direction_max_green` için 4/5/6/10/15/20 aday değerleriyle 6 temsili senaryoda (`balanced_traffic`, `right_heavy_traffic`, `single_direction_traffic`, `asymmetric_peak_traffic`, `emergency_peak_traffic`, `mixed_master_scenario`) yapılan tarama, **mevcut değer olan 6'nın test edilen tüm değerler arasında en iyi (veya en iyiye çok yakın) sonucu verdiğini** gösterdi — hem ortalama bekleme hem de p95/p99/max_wait tail-latency metriklerinde. Neden: `multi_direction_max_green`'i yükseltmek, bir yönün tek bir fazda çok daha uzun yeşil almasına izin verir; ama cycle-fairness her aktif yönü yine de bir turda bir kez servis ettiği için, bu tek yönün uzayan fazı **tüm turun** (cycle length) uzamasına yol açar — bu da her yönün kendi sırasını bekleme süresini artırır (klasik "kısa cycle length ortalama gecikmeyi düşürür" etkisi). `queue_count/discharge_rate` formülü kendi başına "bu yönü temizlemek için ne kadar gerekli" sorusuna doğru cevap veriyor olsa da, DİĞER yönlerin o sürede sıfır servis aldığı gerçeğini görmezden geliyor — clamp, bu sistem-seviyesi maliyeti fiilen fiyatlandıran (kaba ama etkili) bir düzeltme.

Sonuç: `multi_direction_max_green=6` değişmedi (v1 ile aynı). Bu, "kademeli iyileştirme, ölç, sonra devam et" yaklaşımının somut bir çıktısı — bir varsayım test edildi ve yanlış çıktı, kod gereksiz yere karmaşıklaştırılmadı.

## `yolo` provider için strateji: henüz yazılmadı

`state_providers/yolo_provider.py` şu an bir placeholder — gerçek algılama yok. Bu placeholder'ı tüketecek strateji de **henüz yazılmadı**; gerçek YOLO/CV entegrasyonu geldiğinde sıfırdan tasarlanacak, bu projenin önceki adaptive-controller kodlarından hiçbiri yeniden kullanılmayacak. `docs/ground_truth_final_state_and_gaps.md`, o strateji yazıldığında karşılaştırılacak hedef metrikleri (ground truth'un ulaştığı sonuçlar) şimdiden belgeliyor.
