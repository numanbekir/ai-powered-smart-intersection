# Senaryo Talebi ve Kapasite

Senaryoların trafik yoğunluğu, ölçülen kapasiteye oranla (v/c) tanımlanır. Bu dosya kapasitenin nasıl ölçüldüğünü, senaryoların hangi orana ayarlandığını ve gerçek kavşak kayıtlarıyla ilişkiyi anlatır.

## Ölçülen kapasite

`tools/measure_current_capacity.py` tek bir yönü sürekli yeşilde tutar, o yöne kesintisiz talep verir ve geçen araç sayısını süreye böler.

Sonuç: yön başına 1,00 araç/sn. İki şerit vardır, her şeritten 2 saniyede bir araç geçer.

## Talep nasıl üretilir

Araç üretici her `spawn_interval` simülasyon saniyesinde bir araç üretir. Aracın yönü `direction_density` ağırlıklarıyla seçilir. Bu ağırlıklar toplam talebi değil, talebin yönlere dağılımını belirler.

```
v/c = (1 / spawn_interval) / kapasite
```

Bu oran sarı süresindeki kaybı içermez, gerçek doluluk biraz daha yüksektir.

## Senaryoların oranları

| `spawn_interval` | v/c | Senaryolar |
|---:|---:|---|
| 6,66 | 0,15 | `idle_intersection` |
| 4,99 | 0,20 | `sparse_traffic`, `emergency_sparse_traffic` |
| 2,86 | 0,35 | `low_traffic` |
| 2,22 | 0,45 | `emergency_low_frequency_mixed_traffic` |
| 1,82 | 0,55 | `balanced_traffic`, `right_heavy_traffic`, `vertical_heavy_traffic`, `turn_heavy_traffic`, `extreme_directional_traffic`, `direction_shift_traffic`, `emergency_balanced_traffic`, `emergency_right_heavy_traffic` |
| 1,54 | 0,65 | `single_direction_traffic`, `burst_traffic`, `alternating_heavy_traffic`, `turning_conflict_traffic` |
| 1,11 | 0,90 | `peak_traffic`, `asymmetric_peak_traffic`, `emergency_peak_traffic` |

`demand_shift_traffic` ve `mixed_master_scenario` koşu içinde yoğunluk değiştirir (`dynamic_spawn_interval_schedule`). `mixed_master_scenario` diğer senaryoları 90 saniyelik bölümler hâlinde art arda çalıştıran 30 dakikalık bir koşudur.

Talebi tek yöne yığan senaryolarda (`right_heavy`, `extreme_directional`, `asymmetric_peak`) o yönün kendi oranı tablodaki değerden yüksektir, yön tek başına doygunluğa ulaşabilir.

## Gerçek kavşak kayıtlarıyla ilişki

Üç kavşakta 5-10 dakikalık kayıt alındı. Her yeşil faz için yeşilin başlangıcı, ilk aracın geçişi, yeşilin bitişi ve geçen araç sayısı elle işaretlendi (`data/real_world_calibration.csv`, 22 faz). `tools/real_world_calibration_analysis.py` ile özetlenir:

| | Kayıtlar | Simülasyon |
|---|---:|---:|
| Boşalma hızı (yön başına, 2 şerit) | ortalama 0,45 araç/sn | 1,00 araç/sn |
| Yeşilden ilk aracın geçişine kadar süre | ortalama 2,95 sn | yaklaşık 2 sn |

Simülasyon kayıtların yaklaşık iki katı hızlı boşaltır. Önceki sürümde araçlar arası mesafe büyütülerek kapasite kayıtlara eşitlenmişti, ancak araçlar ekranda gerçekçi olmayan boşluklarla ilerliyordu. Hareket modeli yeniden yazılırken ivmelenme, fren ve takip kuralları gözle doğru görünen davranışa göre kuruldu ve kapasite 1,00 araç/sn oldu.

Senaryolardaki v/c oranları korundu: bütün `spawn_interval` değerleri eski ve yeni kapasitenin oranıyla (0,4775) çarpıldı. Bunun sonucu şudur:

- Kontrolcülerin birbirine göre karşılaştırması geçerlidir, çünkü hepsi aynı kapasite ve aynı doluluk oranında koşar.
- Saniye cinsinden mutlak bekleme süreleri ve saatlik araç sayıları gerçek bir kavşağa doğrudan taşınamaz.

Kayıtlar tek yönü gösteren kısa videolardır ve bir kısmında kuyruk yeşil bitmeden boşalmıştır. Bu yüzden 0,45 araç/sn doygun kapasitenin alt sınırına yakın bir değerdir.
