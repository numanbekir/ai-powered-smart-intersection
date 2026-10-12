from controllers.strategies.optimal_ground_truth_strategy import (
    OptimalGroundTruthStrategy,
    get_direction_max_stopped_wait,
)


class RollingHorizonGroundTruthStrategy(OptimalGroundTruthStrategy):
    """`OptimalGroundTruthStrategy`'nin tek-adım (greedy) normal-trafik
    kararını, birkaç faz ileriyi birlikte değerlendiren sınırlı bir arama ile
    değiştirir. Emergency kısa-devresi (`choose_emergency_phase`) miras
    alınır, değişmez -- yalnızca `choose_normal_phase` override edilir.

    Motivasyon: tek-adım greedy + cycle-fairness + süre-ölçekleme
    (`OptimalGroundTruthStrategy`), "sıralama adaleti" ile "verimlilik"
    arasında sürekli birbirini törpüleyen iki ayrı yama gerektirdi.
    İleriye bakan bir planlayıcı bu
    gerginliği ayrı yamalar yerine TEK bir maliyet fonksiyonunun içinde
    çözmeyi hedefler: "şimdi bu yöne uzun yeşil versem, 1-2 faz sonra
    diğer yönlerin kuyruğu ne olur" sorusunu doğrudan sorar.

    Mekanizma (receding-horizon / MPC tarzı):
      1. Her karar noktasında (zamanlama değişmez -- hâlâ en taze veriyle),
         önümüzdeki `rolling_horizon_depth` fazı (varsayılan 2) kapsayan bir
         arama yapılır. Her adımda, o andaki aktif her yön için birkaç aday
         süre üretilir (`build_candidate_durations`): min_green ve
         queue/discharge_rate tabanlı "uzun" seçenek.
      2. Her aday (yön, süre) için gelecekteki kuyruk durumu projekte edilir
         (`project_state`): seçilen yönün kuyruğu discharge_rate kadar
         azalır, TÜM yönlerin kuyruğu (seçilen dahil) öğrenilen
         arrival_rate kadar büyür (elapsed = süre + yellow_time).
      3. Her tam dizinin maliyeti (`state_cost`) iki terimden oluşur:
         (a) her adımdaki projekte kuyruk uzunluklarının karelerinin
         toplamı -- dışbükey, tek bir yönün kuyruğunun aşırı büyümesini
         orantısız cezalandırır; (b) `rolling_horizon_fairness_weight *
         projekte edilen max_wait toplamı` -- gerçek (ground-truth)
         bekleme süresine dayalı, doğrusal bir adalet terimi (bkz. aşağıdaki
         "bulunan ve düzeltilen kendi kendini besleyen açlık" notu).
      4. En düşük toplam maliyetli dizinin yalnızca İLK adımı uygulanır; bir
         sonraki karar noktasında en taze durumla baştan aranır.

    `arrival_rate`, `discharge_rate`'e simetrik şekilde öğrenilir: her karar
    noktasında, bir önceki karardan bu yana AKTİF OLARAK SERVİS EDİLMEMİŞ
    yönlerin kuyruk artışı gözlemlenip EMA ile güncellenir (servis edilen
    yönün kendi gözlemi discharge ile karıştığından hariç tutulur).

    Bulunan ve düzeltilen kendi kendini besleyen açlık: İlk sürümde maliyet
    yalnızca queue^2 idi. `discharge_rate` yalnızca GERÇEKTEN servis edilen
    yön için öğrenildiğinden, nadiren servis edilen bir yön düşük (0'a
    yakın) bir discharge_rate ile kalıyor -- bu da aramaya o yönü servis
    etmenin "verimsiz" (kuyruğu yavaş azaltıyor) göründüğünü söylüyor,
    böylece o yön bir daha az seçiliyor, discharge_rate'i hiç
    öğrenemiyor -- kendi kendini besleyen bir açlık döngüsü (smoke testte
    `right_heavy_traffic`'te `down`/`up` discharge_rate=0.0'da kilitlenip
    kuyrukları sınırsız büyürken gözlemlendi). Ground-truth'un gerçek
    `max_wait` verisine dayanan (b) terimi, discharge_rate tahminindeki bu
    yanlılıktan bağımsız olduğu için döngüyü kırıyor.

    Bilinen sınırlama: sonlu ufuk (`rolling_horizon_depth`) ötesinde hâlâ
    miyop bir sistemdir. Testlerde per-direction max_wait izlenerek açlık
    paterni olup olmadığı ayrıca kontrol edilmelidir.

    Bulunan ve düzeltilen iki YAPISAL hata (2026-07-18, canlı
    GUI'deki "green_time neredeyse hep aynı, fixed gibi çalışıyor" gözlemiyle
    tetiklendi -- headless doğrulamada `peak_traffic`'te kuyruk 10'a çıksa
    bile 14/14 kararın tam olarak `min_green` verdiği doğrulandı):
      1. `state_cost`'un adalet terimi ham `wait_clock` topluyordu (eşiksiz).
         `project_state`, servis edilmeyen her yönün wait_clock'unu adayın
         `elapsed`'i kadar artırdığından, daha uzun bir yeşil adayı diğer 3
         yöne `fairness_weight * 3 * Δelapsed` kadar KESİN ve DOĞRUSAL bir
         ek maliyet yüklüyordu -- buna karşılık kazanç (queue² teriminin
         küçülmesi) kuyruk boşalınca sıfırlanıyordu (azalan getiri).
         Düzeltme: `OptimalGroundTruthStrategy`'nin `excess_wait` mantığıyla
         aynı -- yalnızca `starvation_soft_limit`'i (varsayılan 20s) aşan
         bekleme cezalandırılır.
      2. Bu tek başına yetmedi: farklı sürelerdeki adaylar aynı `depth`
         sayıda adımı kapsıyor ama FARKLI toplam zaman aralığını kapsıyordu
         (ör. kök adayı 5s olan bir dal ile 18s olan bir dal, aynı depth=2
         aramada çok farklı toplam süreye yayılıyordu) -- ham toplam
         maliyeti doğrudan karşılaştırmak, uzun bir dalı sırf daha uzun bir
         zaman aralığı (dolayısıyla diğer yönler için daha fazla birikmiş
         büyüme) kapsadığı için sistematik olarak cezalandırıyordu.
         Düzeltme: `search_best_action` artık adayları toplam maliyete göre
         değil, birim-zaman başına maliyet oranına (`total_cost /
         total_elapsed`) göre karşılaştırıyor.
      Bu iki hata birlikte hem v1 hem v2'yi (fairness_weight'in 10.0 veya
      3.0 olması farketmeksizin, mekanizma aynı) etkiliyordu -- yani bu
      tarihten önce üretilen tüm RH v1/v2 karşılaştırma sonuçları bu
      hatayla ölçülmüştü.
    """

    strategy_key = "rolling_horizon_ground_truth"

    # Panel/debug: direction_debug'daki "score" alani burada projekte
    # edilmis toplam maliyettir -- dusuk olan yon kazanir (v3'un tersine).
    score_semantics = {"label": "projected cost (lower=better)", "higher_is_better": False}

    def ensure_runtime_state(self, engine):
        super().ensure_runtime_state(engine)

        if not hasattr(engine, "rolling_horizon_arrival_tracking"):
            engine.rolling_horizon_arrival_tracking = {
                "last_served": None,
                "observations": {
                    direction: None for direction in self.DIRECTIONS
                },
            }

        for direction in self.DIRECTIONS:
            engine.optimal_direction_runtime[direction].setdefault("arrival_rate", 0.0)

    def update_arrival_rate_estimates(self, engine, queue_counts, params):
        tracking = engine.rolling_horizon_arrival_tracking
        now = engine.simulation_elapsed
        alpha = float(params.get("rolling_horizon_arrival_rate_alpha", 0.35))
        just_served = tracking["last_served"]

        for direction in self.DIRECTIONS:
            observation = tracking["observations"][direction]

            # Servis edilen yönün kendi gözlemi discharge ile karıştığından
            # (kuyruk hem azalıp hem araç alıyor) arrival_rate tahminine
            # dahil edilmez -- yalnızca servis edilmeyen yönlerin kuyruk
            # artışı saf varış sinyali verir.
            if observation is not None and direction != just_served:
                dt = now - observation["time"]

                if dt > 0:
                    observed_rate = max(
                        0.0, (queue_counts[direction] - observation["queue"]) / dt
                    )
                    runtime = engine.optimal_direction_runtime[direction]
                    runtime["arrival_rate"] = (
                        alpha * observed_rate + (1 - alpha) * runtime["arrival_rate"]
                    )

            tracking["observations"][direction] = {
                "queue": queue_counts[direction],
                "time": now,
            }

    def build_candidate_durations(self, direction, queue, discharge_rate, params):
        min_green = int(params.get("min_green", 5))
        max_green = int(params.get("max_green", 30))

        effective_rate = max(
            discharge_rate, float(params.get("min_effective_discharge_rate", 0.3))
        )
        raw = queue / effective_rate if effective_rate > 0 else min_green
        long_option = int(max(min_green, min(max_green, round(raw))))

        return sorted(set([min_green, long_option]))

    def build_candidates(self, queue_counts, discharge_rates, params):
        candidates = []

        for direction in self.DIRECTIONS:
            queue = queue_counts[direction]

            if queue <= 0:
                continue

            for duration in self.build_candidate_durations(
                direction, queue, discharge_rates[direction], params
            ):
                candidates.append((direction, duration))

        return candidates

    def estimate_direction_growth(self, direction, elapsed, time_so_far, arrival_rates, discharge_rates):
        # Bu karar turunda `direction` yonune, `time_so_far` ile
        # `time_so_far+elapsed` arasinda katilmasi beklenen arac sayisi.
        # Taban (v1) davranisi: ogrenilen arrival_rate EMA'siyla dogrusal
        # ekstrapolasyon -- EMA zaten zaman-bagimsiz bir oran oldugundan
        # time_so_far'i kullanmaz, discharge_rates'i de kullanmaz (yalnizca
        # V2'nin tavanlama mantigi icin sinyaturda tutuluyor). `discharge_rates`
        # burada kullanilmiyor. `RollingHorizonGroundTruthV2Strategy` bu
        # metodu ground-truth-kesin bir ETA sayimiyla override eder (bkz.
        # o siniftaki docstring).
        return arrival_rates[direction] * elapsed

    def growth_reason_fragment(self, direction, arrival_rates, discharge_rates, elapsed):
        # `choose_normal_phase`'in reason metnindeki, buyume varsayimini
        # aciklayan parca -- V2, gercek mekanizmayi yansitmasi icin bunu
        # override eder (aksi halde metin hala "arrival_rate" diyip
        # GUI'de gosterilen karar aciklamasini yanlis
        # yonlendirirdi).
        return f"arrival_rate={arrival_rates[direction]:.2f} veh/s, "

    def direction_debug_growth_fields(self, direction, arrival_rates, discharge_rates, elapsed):
        # Panelin direction_debug tablosundaki buyume-ile-ilgili alan(lar) --
        # ayni nedenle (bkz. growth_reason_fragment) override edilebilir.
        return {"arrival_rate": round(arrival_rates[direction], 2)}

    def project_state(self, queue_counts, wait_clock, direction, duration, discharge_rates, arrival_rates, yellow_time, time_so_far):
        elapsed = duration + yellow_time
        projected_queues = {}
        projected_wait = {}

        for d, queue in queue_counts.items():
            if d == direction:
                discharged = discharge_rates[d] * duration
                queue = max(0.0, queue - discharged)

            queue += self.estimate_direction_growth(d, elapsed, time_so_far, arrival_rates, discharge_rates)
            projected_queues[d] = queue

            # Servis edilen yonun "en eski bekleyen" saati sifirlanir;
            # digerleri icin gecen sureyi biriktiriyoruz -- gercek
            # simulasyondaki waitTime artisiyla ayni mantik (bkz.
            # Vehicle.update_signal_wait_time), burada projekte ediliyor.
            projected_wait[d] = 0.0 if d == direction else wait_clock[d] + elapsed

        return projected_queues, projected_wait

    def state_cost(self, queue_counts, wait_clock, fairness_weight, starvation_soft_limit=20.0):
        # discharge_rate ogrenilmemis (0.0'a yakin) bir yon, sirf az
        # servis edildigi icin "verimsiz" gorunup arama tarafindan bir
        # daha az secilebilir -- kendi kendini besleyen bir acliktir
        # (bu strateji ilk yazildiginda gozlendi). queue^2 tek basina bu
        # donguyu kirmiyor: kisa vadede az servis edilen bir yonun
        # kuyrugu buyuk olsa bile, o yonu secmenin "verimsiz" gorunen
        # maliyeti (dusuk ogrenilmis discharge_rate) onu hep ikinci
        # plana itebiliyordu. Gercek (ground-truth) bekleme suresine
        # dayanan bu ikinci terim, discharge_rate tahminindeki
        # yanlilikdan bagimsiz, dogrudan "ne kadar uzun zamandir
        # bekliyor" sinyalini maliyete ekleyip donguyu kirar.
        #
        # NOT (bulunan ve duzeltilen ikinci bir yapisal hata): bu terim
        # onceden raw wait_clock (esiksiz, sifirdan itibaren) topluyordu.
        # project_state, servis edilmeyen HER yonun wait_clock'unu
        # secilen adayin `elapsed` (duration+yellow_time) kadar
        # artiriyor -- yani daha uzun bir yesil adayi, diger 3 yonun
        # wait_clock'una `fairness_weight * 3 * Δelapsed` kadar KESIN
        # ve DOGRUSAL bir ek maliyet yukluyordu. Buna karsilik uzun
        # yesilin kazanci (secilen yonun queue^2 teriminin kuculmesi)
        # kuyruk bosalinca SIFIRLANIYOR (azalan getiri). Sonuc: tipik
        # kuyruk buyukluklerinde (2-10 arac) bu dogrusal ceza azalan-
        # getirili kazanci sistemik olarak eziyor, arama neredeyse HER
        # zaman en kisa (min_green) adayi secip yesil suresi kuyruktan
        # tamamen bagimsiz kaliyordu (canli GUI'de ve headless
        # dogrulamada: peak_traffic'te kuyruk 10'a ciksa bile 14/14
        # karar tam olarak min_green). Duzeltme: OptimalGroundTruthStrategy'nin
        # zaten dogru calisan `excess_wait` mantigiyla ayni -- yalnizca
        # `starvation_soft_limit`'i ASAN bekleme cezalandirilir. Makul
        # bekleme sureleri (<20s) adalet terimine SIFIR maliyet yukler,
        # arama artik gercekten backlogged bir yone uzun yesil vermekten
        # cekinmez; bir yon GERCEKTEN aclige yaklasirken (>20s) terim
        # yine devreye girip aramayi frenler.
        cost = sum(q * q for q in queue_counts.values())
        cost += fairness_weight * sum(
            max(0.0, w - starvation_soft_limit) for w in wait_clock.values()
        )
        return cost

    def search_best_action(
        self,
        queue_counts,
        wait_clock,
        depth,
        discharge_rates,
        arrival_rates,
        params,
        yellow_time,
        time_so_far=0.0,
        allowed_directions=None,
        capture_candidates=None,
    ):
        candidates = self.build_candidates(queue_counts, discharge_rates, params)

        if allowed_directions is not None:
            candidates = [c for c in candidates if c[0] in allowed_directions]

        if not candidates or depth <= 0:
            return 0.0, 0.0, None

        fairness_weight = float(params.get("rolling_horizon_fairness_weight", 1.0))
        starvation_soft_limit = float(params.get("starvation_soft_limit", 20.0))
        best_rate = None
        best_cost = None
        best_elapsed = None
        best_action = None

        for direction, duration in candidates:
            projected_queues, projected_wait = self.project_state(
                queue_counts, wait_clock, direction, duration, discharge_rates, arrival_rates, yellow_time, time_so_far
            )
            step_cost = self.state_cost(projected_queues, projected_wait, fairness_weight, starvation_soft_limit)

            elapsed = duration + yellow_time
            remaining_cost, remaining_elapsed, _ = self.search_best_action(
                projected_queues, projected_wait, depth - 1, discharge_rates, arrival_rates, params, yellow_time,
                time_so_far=time_so_far + elapsed,
            )

            total_cost = step_cost + remaining_cost
            total_elapsed = elapsed + remaining_elapsed

            # BULUNAN VE DUZELTILEN UCUNCU YAPISAL HATA: farkli sureli
            # adaylar, depth kadar ADIM ileriyi kapsiyor, ama ayni sayida
            # adim FARKLI toplam SURE anlamina geliyor (ör. kok adayi 5s
            # olan bir dal ile 18s olan bir dal, ayni depth=2'de cok
            # farkli toplam zaman araligini kapsar). Ham total_cost'u
            # dogrudan karsilastirmak, uzun bir dalin sirf DAHA UZUN bir
            # zaman araligini (dolayisiyla diger yonler icin daha fazla
            # birikmis buyume) kapsadigi icin sistematik olarak
            # cezalandirilmasina yol aciyordu -- state_cost'taki adalet
            # terimi duzeltildikten SONRA bile (bkz. state_cost'un ust
            # yorumu) ayni "hep min_green" semptomu bu yuzden devam etti
            # (headless dogrulama: peak_traffic'te kuyruk=9 iken bile
            # green=5 secildi). Duzeltme: adaylari toplam maliyete gore
            # degil, birim-zaman basina maliyet oranina (rate = total_cost
            # / total_elapsed) gore karsilastir -- boylece farkli sureli
            # secenekler, kapsadiklari zaman araligindan bagimsiz,
            # adil/ozdes bir olcekte karsilastirilir.
            rate = total_cost / total_elapsed if total_elapsed > 0 else total_cost

            # `capture_candidates` yalnizca panel/debug amacli -- verilirse
            # (sadece KOK cagrida verilir, rekursif cagrilar None birakir)
            # her (yon, sure) adayinin karsilastirilan degerini (rate)
            # disariya tasir, boylece "uzun secenek gercekten
            # degerlendiriliyor mu, neden kaybediyor" sorusu panelde
            # dogrudan gorulebilir.
            if capture_candidates is not None:
                capture_candidates.append(
                    {"direction": direction, "duration": duration, "cost": rate}
                )

            if best_rate is None or rate < best_rate:
                best_rate = rate
                best_cost = total_cost
                best_elapsed = total_elapsed
                best_action = (direction, duration)

        return best_cost, best_elapsed, best_action

    def choose_normal_phase(self, state, params, engine):
        min_green = int(params.get("min_green", 5))
        current_direction = engine.directionNumbers.get(engine.controller.currentGreen, None)

        queue_counts = {d: float(state.get(d, 0)) for d in self.DIRECTIONS}
        active_directions = [d for d in self.DIRECTIONS if queue_counts[d] > 0]

        self.update_arrival_rate_estimates(engine, queue_counts, params)

        if not active_directions:
            fallback_direction = current_direction or self.DIRECTIONS[0]
            engine.rolling_horizon_arrival_tracking["last_served"] = None

            return (
                fallback_direction,
                min_green,
                (
                    "No active demand on any direction; holding current direction "
                    "at minimum green."
                ),
                {
                    "emergency_priority": False,
                    "direction_debug": self.build_simple_direction_debug(
                        engine, fallback_direction
                    ),
                    "score_semantics": self.score_semantics,
                },
            )

        discharge_rates = {
            d: max(
                engine.optimal_direction_runtime[d]["discharge_rate"],
                float(params.get("min_effective_discharge_rate", 0.3)),
            )
            for d in self.DIRECTIONS
        }
        arrival_rates = {
            d: engine.optimal_direction_runtime[d]["arrival_rate"]
            for d in self.DIRECTIONS
        }

        horizon_depth = int(params.get("rolling_horizon_depth", 2))
        yellow_time = float(params.get("yellow_time", 3))

        # Reason/debug metninde gosterilen buyume rakami icin temsili bir
        # pencere -- aramanin GERCEKTEN kullandigi degisken (aday-suresine
        # bagli) pencerelerin tam yerine gecmez, ama "bir sonraki faz
        # kadar suren bir pencerede ne bekleniyor" seklinde tutarli,
        # anlasilir bir gosterim saglar (bkz. growth_reason_fragment /
        # direction_debug_growth_fields).
        reporting_elapsed = min_green + yellow_time

        wait_clock = {
            d: get_direction_max_stopped_wait(engine, d) for d in self.DIRECTIONS
        }

        self.reset_cycle_if_completed(engine, active_directions)

        root_candidates = []

        best_cost, _, best_action = self.search_best_action(
            queue_counts,
            wait_clock,
            horizon_depth,
            discharge_rates,
            arrival_rates,
            params,
            yellow_time,
            capture_candidates=root_candidates,
        )

        best_direction, green_time = best_action

        # Cycle-fairness: v3'un (OptimalGroundTruthStrategy) sahip oldugu sert
        # garantinin ayni -- turda henuz servis edilmemis aktif bir yon varsa
        # ve aramanin ozgur secimi zaten servis edilmisse, arama SADECE
        # unserved yonler arasindan tekrarlanip oradaki en iyi aksiyona
        # yonlendirilir. Onceden bu strateji choose_normal_phase'i tamamen
        # override ettigi icin bu garantiyi hic miras almiyordu -- yalnizca
        # yumusak fairness_weight*wait_clock cezasi vardi, bu da ayni yonun
        # cycle tamamlanmadan tekrar secilmesini engellemiyordu (gercek batch
        # verisiyle dogrulandi). Yalnizca KOK karar bu sekilde kisitlanir;
        # search_best_action'in kendi ic (lookahead) rekursiyonu -- v3'un
        # projeksiyonlarinda da oldugu gibi -- kisitlanmaz. `params.cycle_fairness_enabled=False`
        # iken bu kisit tamamen devre disi -- kok karar aramanin ozgur secimiyle kalir.
        unserved_directions = (
            self.get_unserved_active_directions(engine, active_directions)
            if bool(params.get("cycle_fairness_enabled", True))
            else []
        )
        cycle_note = ""

        if unserved_directions and best_direction not in unserved_directions:
            restricted_cost, _, restricted_action = self.search_best_action(
                queue_counts,
                wait_clock,
                horizon_depth,
                discharge_rates,
                arrival_rates,
                params,
                yellow_time,
                allowed_directions=unserved_directions,
                capture_candidates=root_candidates,
            )

            if restricted_action is not None:
                redirected_from = best_direction
                best_direction, green_time = restricted_action
                best_cost = restricted_cost
                cycle_note = (
                    f" Cycle-fairness: {redirected_from.upper()} already served this "
                    f"cycle, redirected to unserved {best_direction.upper()}."
                )

        engine.optimal_phase_tracking = {
            "direction": best_direction,
            "green_time": green_time,
            "crossed_before": self.get_direction_crossed(engine, best_direction),
        }

        engine.rolling_horizon_arrival_tracking["last_served"] = best_direction

        reason = (
            f"{best_direction.upper()} selected by Rolling-Horizon Ground-Truth Strategy. "
            f"queue={queue_counts[best_direction]:.0f}, "
            f"discharge_rate={discharge_rates[best_direction]:.2f} veh/s, "
            f"{self.growth_reason_fragment(best_direction, arrival_rates, discharge_rates, reporting_elapsed)}"
            f"max_wait={wait_clock[best_direction]:.1f}s, "
            f"green_time={green_time}s, "
            f"horizon_depth={horizon_depth}, projected_cost={best_cost:.1f}. "
            f"Karar, önümüzdeki {horizon_depth} fazı birlikte değerlendiren bir "
            f"aramanın ilk adımıdır -- tek başına greedy değil."
            f"{cycle_note}"
        )

        served_before_this_pick = set(engine.optimal_cycle_state.get("served_directions", set()))

        best_candidate_by_direction = {}
        for candidate in root_candidates:
            d = candidate["direction"]
            if d not in best_candidate_by_direction or candidate["cost"] < best_candidate_by_direction[d]["cost"]:
                best_candidate_by_direction[d] = candidate

        direction_debug = {}
        for direction in self.DIRECTIONS:
            best_candidate = best_candidate_by_direction.get(direction)
            direction_debug[direction] = {
                "queue": queue_counts[direction],
                "active": direction in active_directions,
                "score": round(best_candidate["cost"], 1) if best_candidate else None,
                "candidate_duration": best_candidate["duration"] if best_candidate else None,
                "excess_wait": round(wait_clock[direction], 1),
                "discharge_rate": round(discharge_rates[direction], 2),
                **self.direction_debug_growth_fields(direction, arrival_rates, discharge_rates, reporting_elapsed),
                "served_this_cycle": direction in served_before_this_pick,
                "chosen": direction == best_direction,
                "emergency": False,
            }

        return (
            best_direction,
            green_time,
            reason,
            {
                "emergency_priority": False,
                "direction_debug": direction_debug,
                "score_semantics": self.score_semantics,
            },
        )


class RollingHorizonGroundTruthV2Strategy(RollingHorizonGroundTruthStrategy):
    """`RollingHorizonGroundTruthStrategy`'nin ayni MPC-tarzi arama iskeletini
    (candidate uretimi, kareli-kuyruk + gercek-bekleme maliyeti,
    cycle-fairness redirect) aynen kullanir; yalnizca projeksiyondaki
    "yakin gelecek talep" buyume terimini degistirir.

    Taban sinif bu terimi `arrival_rate` adinda ogrenilmis bir EMA ile
    dolduruyor -- bu EMA yalnizca bir yon SERVIS EDILMEDIGINDE gozlemlenen
    kuyruk artisindan cikariliyor (bkz. `update_arrival_rate_estimates`):
    gecikmeli (soguk baslangicta 0.0) ve istatistiksel bir yaklastirma.
    Ground truth'ta buna gerek yok -- her yaklasan (crossed==0, henuz
    `waitingDueToSignalQueue==False`, yani henuz kuyruga resmen KATILMAMIS)
    aracin stop-line'a olan mesafesi ve hizi zaten biliniyor, dolayisiyla
    "onumuzdeki N saniyede bu yone KAC arac gercekten katilacak" sorusu bir
    oranla degil, DOGRUDAN SAYIMLA cevaplanabilir. ETA hesabi icin
    `OptimalGroundTruthStrategy.eta_seconds` AYNEN yeniden kullanilir --
    saf serbest-akis (distance/hiz) DEGIL: ilk denemede sadece serbest-akis
    kullanilmisti ("henuz kuyruga girmemis = bloke degil" varsayimiyla),
    ama pilot olcumunde mixed_master_scenario'da (doygun rejim) tail-latency
    kotulesti (p99 +%15.8) -- cunku yogun trafikte "waitingDueToSignalQueue"
    bayragi henuz almamis bir arac bile, ONUNDE serbest ilerleyen ama ondan
    da yavas baska araclar oldugunda GERCEKTE cok daha yavas geliyor;
    saf serbest-akis bu durumda ETA'yi ciddi sekilde kucuk gosterip aramaya
    yanlis bir "yakin gelecekte buyuk bir yaklasma dalgasi var" sinyali
    veriyordu. `eta_seconds`, aynen emergency araclar icin zaten yaptigi
    gibi (bkz. o metodun ust dokumantasyonu), free-flow ETA'yi
    vehicles_ahead_count/discharge_rate tabanli bir kuyruk-bosalma
    tahminiyle karsilastirip BUYUK olani alarak bu ayni sinif hatayi
    (bu kez emergency degil, sıradan yaklasan araclar icin) duzeltiyor.

    Panelin "gorunur/gorunmez" (900x900 render alani) ayrimi kasitli olarak
    KULLANILMIYOR -- o salt bir render siniri, algoritmik anlami yok;
    ground truth'un mesafe/hiz verisinden hesaplanan surekli bir ETA, o
    ikili esikten daha isabetli.

    Mekanizma: her karar turunun basinda (`choose_normal_phase` girisinde,
    arama baslamadan once) her yon icin yaklasan araclarin ETA'lari bir kez
    hesaplanip `self._approaching_etas`'a alinir (arama boyunca sabit
    kalir -- ayni discharge_rate/arrival_rate'in de arama boyunca sabit
    varsayilmasiyla ayni yaklastirma seviyesi). `estimate_direction_growth`
    hook'u, arama agacinin her adiminda o adimin kapsadigi
    [time_so_far, time_so_far+elapsed) zaman penceresine dusen ETA sayisini
    dondurur -- boylece ayni yaklasan arac birden fazla adimda tekrar
    sayilmaz. Bu deger hem sure/projeksiyon hesabina (`project_state` ->
    `state_cost`) hem de -- aramanin kok adiminin maliyeti bu projeksiyona
    dayandigindan -- yon SECIMINE de otomatik olarak yansir; ayrica bir
    "skor terimi" eklemeye gerek yok.

    Buyume tavani (`rolling_horizon_growth_cap_multiplier`, varsayilan 3.0):
    pilot A/B karsilastirmasinda,
    tavansiz kesin sayim, mixed_master_scenario'da (doygun rejim) tail-
    latency'yi kotulestirdi -- bir yonde birden fazla aracin ayni yakin
    ETA'da kumelenmesi, state_cost'un kareli (queue**2) terimini o kadar
    sismiriyordu ki, ZATEN uzun suredir bekleyen baska bir yonun
    fairness_weight*wait_clock korumasini ezip, henuz gelmemis bir dalgayi
    onceleyebiliyordu (somut ornek icin `estimate_direction_growth`'un
    ust yorumuna bkz.). Tavan, bu yondeki BUYUME'yi o yonun kendi
    discharge_rate'iyle ("gercekte ne kadar hizli isleyebilecegi") oranti
    icinde sinirlar -- boylece daha yogun bir yon hala daha yuksek bir
    buyume degeri uretir (sira dogru sekilde etkilenir), ama tek bir anlik
    kumelenme fairness teriminin agirligini artik ezemez.
    """

    strategy_key = "rolling_horizon_ground_truth_v2"

    _approaching_etas = None
    _growth_cap_multiplier = 3.0
    _min_effective_discharge_rate = 0.3

    def collect_approaching_etas(self, engine, params):
        # NOT: "henuz kuyruga girmemis (waitingDueToSignalQueue==False)"
        # bir arac SAF SERBEST-AKISTA degildir -- yogun/doygun bir rejimde
        # (ör. mixed_master_scenario), bu aracin onunde ayni seritte
        # henuz kesismedigi HALDE ondan da yavas ilerleyen baska araclar
        # olabilir (henuz teker teker "waitingDueToSignalQueue" bayragi
        # almamis olsalar bile). Sadece distance/hiz kullanmak (pilot
        # olcumunde mixed_master_scenario'da tail-latency'yi kotulestirdi
        # -- p99 +%15.8, max_wait +%7.0: bu ETA'yi ciddi sekilde KUCUK
        # gosterip aramaya, gercekte cok daha uzun surede gelecek bir
        # "yaklasan burst"u yanlislikla cok yakin gosteriyordu) bu
        # projenin ONCEDEN emergency araclar icin bulup duzelttigi ayni
        # hatanin bir varyanti (bkz. OptimalGroundTruthStrategy.eta_seconds).
        # Duzeltme: ayni genel/arac-turu-bagimsiz `eta_seconds` metodunu
        # (free-flow ETA'yi, onundeki servis-edilmemis arac sayisi /
        # discharge_rate ile karsilastirip BUYUK olani alan) burada da
        # kullan -- yeni bir hesap yazmaya gerek yok, zaten genel.
        etas = {direction: [] for direction in self.DIRECTIONS}

        for direction in self.DIRECTIONS:
            for lane in self.ACTIVE_LANES:
                for vehicle in engine.vehicles[direction][lane]:
                    if getattr(vehicle, "crossed", 0) != 0:
                        continue
                    if getattr(vehicle, "waitingDueToSignalQueue", False):
                        continue

                    distance = self.distance_to_stop_line(engine, vehicle, direction)

                    if distance is None:
                        continue

                    eta = self.eta_seconds(engine, vehicle, distance, params)

                    if eta is not None:
                        etas[direction].append(eta)

        for direction in self.DIRECTIONS:
            etas[direction].sort()

        return etas

    def estimate_direction_growth(self, direction, elapsed, time_so_far, arrival_rates, discharge_rates):
        etas = (self._approaching_etas or {}).get(direction, [])
        window_end = time_so_far + elapsed

        exact_count = float(sum(1 for eta in etas if time_so_far < eta <= window_end))

        # Kesin sayim, ozellikle doygun rejimde (mixed_master_scenario pilot
        # olcumunde gozlendi), bir yonde birkac aracin ayni yakin ETA'da
        # kumelenmesiyle BUYUK bir tek-adimlik sicrama uretebiliyor. Bu
        # sicrama, state_cost'taki queue**2 terimi (dogasi geregi buyuk
        # degerleri oransiz agirliklandirir) uzerinden, HENUZ gelmemis bir
        # dalgayi, ZATEN uzun suredir bekleyen (fairness_weight*wait_clock
        # ile korunmasi gereken) bir yonun onune gecirebiliyordu --
        # dogrulanan somut ornek: LEFT (queue=5, excess_wait=20.3s) yerine
        # RIGHT (queue=2, ama 22 yaklasan arac) secilmisti, bu da LEFT'in
        # zaten uzun bekleme suresini gereksiz uzatip p95/p99/max_wait'i
        # kotulestirdi.
        # Duzeltme: bu yondeki buyumeyi, o yonun KENDI discharge_rate'iyle
        # ("gercekte ne kadar hizli isleyebilecegi") oranti icinde bir
        # TAVANLA sinirla -- gercek buyume sinyali kalir (yogun yonler yine
        # daha yuksek deger uretir, sira dogru sekilde etkilenir) ama tek
        # bir anlik kumelenme artik fairness teriminin agirligini ezemez.
        discharge_rate = max(discharge_rates[direction], self._min_effective_discharge_rate)
        cap = self._growth_cap_multiplier * discharge_rate * elapsed

        return min(exact_count, cap)

    def growth_reason_fragment(self, direction, arrival_rates, discharge_rates, elapsed):
        growth = self.estimate_direction_growth(direction, elapsed, 0.0, arrival_rates, discharge_rates)
        total_approaching = len((self._approaching_etas or {}).get(direction, []))
        return (
            f"beklenen_yeni_arac(~{elapsed:.0f}s)={growth:.1f} "
            f"(toplam_yaklasan={total_approaching}, ground-truth kesin ETA + tavan, EMA degil), "
        )

    def direction_debug_growth_fields(self, direction, arrival_rates, discharge_rates, elapsed):
        growth = self.estimate_direction_growth(direction, elapsed, 0.0, arrival_rates, discharge_rates)
        total_approaching = len((self._approaching_etas or {}).get(direction, []))
        return {
            "arrival_rate": None,
            "expected_new_arrivals": round(growth, 1),
            "total_approaching": total_approaching,
        }

    def choose_normal_phase(self, state, params, engine):
        self._approaching_etas = self.collect_approaching_etas(engine, params)
        self._growth_cap_multiplier = float(params.get("rolling_horizon_growth_cap_multiplier", 3.0))
        self._min_effective_discharge_rate = float(params.get("min_effective_discharge_rate", 0.3))

        try:
            return super().choose_normal_phase(state, params, engine)
        finally:
            self._approaching_etas = None
