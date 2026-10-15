# Karar Kuralı (`controllers/strategies/demand_strategy.py`)

Adaptif kontrolün tek bir karar kuralı vardır: `DemandStrategy`. Kural simülasyonun içini okumaz, yalnızca dört yaklaşım kolunun gözlemini alır. Aynı kod iki farklı gözlemle çalıştırılır:

| Kontrolcü | Gözlem kaynağı |
|---|---|
| `adaptive_ground_truth` (Adaptif - Tam Bilgi) | `GroundTruthStateProvider`: kamera karesine giren araçların kesin sayısı |
| `adaptive_camera` (Adaptif - Kamera) | `YoloStateProvider`: aynı karede YOLO11n tespitleri, simülasyon saniyesinde bir kez |

İki kaynak aynı görüş alanını kullanır. Aralarındaki fark tespit hatasından ve bir saniyelik gözlem aralığından gelir, bu fark kameranın kontrol kalitesine maliyeti olarak ölçülür.

## Gözlem

Her yön için:

- `visible_count`: dur çizgisine henüz gelmemiş, karede görünen araç sayısı. Bir aracın sayılması için en az %30'unun kare içinde olması gerekir.
- `is_saturated`: bir araç kare kenarına 70 pikselden yakınsa doğrudur. Kuyruk büyük olasılıkla kare dışında sürüyordur, sayı alt sınırdır.
- `emergency`: en yakın acil durum aracının türü, dur çizgisine uzaklığı, durup durmadığı ve önündeki araç sayısı. Yoksa `None`.

## Yön seçimi

```
index = araç sayısı + λ · max(0, kırmızı süre − yumuşak sınır)
```

En yüksek indeksli yön seçilir. Bunun üstünde bir tur adaleti kuralı vardır: aracı olan her yön bir kez yeşil almadan hiçbir yön ikinci kez yeşil almaz. Varsayılan değerler λ = 1,5 ve yumuşak sınır 20 sn.

Ölçülen davranış: birden çok yönde araç varken verilen yeşillerin %97-100'ünde seçilen yön en uzun süredir kırmızı olan yöndür. Yani yoğun trafikte sıra pratikte dönüşümlüdür. Kuralın sabit süreden ayrıldığı yer aracı olmayan yönü atlaması ve yeşil süresini araç sayısına göre vermesidir.

## Yeşil süresi

```
yeşil = kalkış süresi + araç sayısı / boşalma hızı   (+ doygunluk payı)
```

Sonuç en kısa ve en uzun yeşil arasına sıkıştırılır. Varsayılanlar: kalkış süresi 2 sn, boşalma hızı 1 araç/sn, doygunluk payı 3 sn, en kısa yeşil 5 sn, en uzun yeşil 30 sn, sarı 3 sn. Doygunluk payı yalnızca `is_saturated` doğruyken eklenir.

Süresi biten yeşil, başka hiçbir yönde araç yokken sarıya geçmeden sürdürülür.

## Acil durum aracı

- Öncelik: acil durum aracı görülen yön sıradaki yeşili alır. Birden çok yönde varsa dur çizgisine en yakın olan seçilir. Yeşil süresi aracın tahmini varış süresi kadardır: uzaklık / hız + önündeki araç başına 1 sn + 2 sn pay.
- Kesme: başka bir yönde acil durum aracı görülürse yanan yeşil, en kısa yeşil süresi dolduktan sonra kesilir.
- Uzatma: yeşil yanan yöndeki acil durum aracı kalan sürede geçemeyecekse yeşil uzatılır. Toplam uzatma 20 sn ile sınırlıdır.
- Açlık koruması: başka bir yön 90 sn'den uzun süredir kırmızıysa öncelik verilmez. Kuyruğa sıkışmış bir acil durum aracının diğer yönleri sınırsız bekletmesi böyle önlenir.

## Kontrolcü ile iş bölümü

`controllers/adaptive_controller.py` zamanlamayı yürütür: yeşil, sarı, birer saniyelik adımlar. Kuralın verdiği kararı değiştirmez. Her yeşilde kural bir de açıklama metni döndürür, panelde "Son karar" olarak gösterilen metin budur.

Parametreler `core/config_defaults.py` içindeki `ADAPTIVE_PARAMS` sözlüğündedir ve `data/controller_versions.json` dosyasına oradan yazılır.

## Kararların denetimi

`tools/verify_decisions.py` her yeşili sonradan olanla karşılaştırır: verilen sürede kaç araç geçti, yeşil son araçtan sonra boşa yandı mı, seçilen yön en kalabalık ya da en uzun bekleyen yön müydü. Aynı senaryolar sabit süreli kontrolle de koşturulur.

Son ölçüm (her senaryoda bir koşu, birden çok yönde araç varken verilen yeşiller):

| Senaryo | Boşa yanan yeşil: sabit | Boşa yanan yeşil: adaptif | Kısa kalan yeşil: adaptif |
|---|---:|---:|---:|
| `low_traffic` | %42 | %25 | %2 |
| `balanced_traffic` | %24 | %17 | %0 |
| `right_heavy_traffic` | %27 | %24 | %3 |
| `peak_traffic` | %0 | %4 | %0 |
| `emergency_balanced_traffic` | %24 | %32 | %0 |

Az ve orta yoğunlukta adaptif kontrol boşa yanan yeşili azaltıyor. Doygun trafikte her yönde kuyruk olduğu için iki kontrolcüde de yeşil neredeyse hiç boşa yanmıyor. Acil durum araçlı senaryoda oran adaptif kontrolde daha yüksek. Muhtemel nedeni, acil durum aracı için verilen ya da uzatılan yeşilin süresinin kuyruğa göre değil aracın varışına göre hesaplanması.

## Bilinen sınırlar

- Gözlem karede görünenle sınırlıdır. Kare dışına taşan kuyruk sayılamaz, doygunluk payı bunu kabaca telafi eder.
- Kare dışında bekleyen acil durum aracı görülmez. Öncelik araç kareye girdiğinde başlar.
- Boşalma hızı ölçülmez, sabit kabul edilir.
- Parametreler tek bir karşılaştırmayla seçildi, senaryo başına ayar yapılmadı.
