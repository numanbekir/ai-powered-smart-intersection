from controllers.strategies.base_strategy import BaseAdaptiveStrategy


def get_direction_max_stopped_wait(engine, direction):
    max_wait = 0.0

    for lane in getattr(engine, "ACTIVE_LANES", [1, 2]):
        for vehicle in engine.vehicles[direction][lane]:
            if getattr(vehicle, "crossed", 0) == 0:
                max_wait = max(
                    max_wait,
                    float(getattr(vehicle, "waitTime", 0.0)),
                )

    return max_wait


class OptimalGroundTruthStrategy(BaseAdaptiveStrategy):
    """Ground truth'un tam bilgi avantajını (her aracın konumu, hızı, bekleme
    süresi bilinir) kullanan, sezgisel ağırlık toplamı yerine kuyruk/zamanlama
    teorisinden gelen az sayıda gerekçeli sabitle çalışan karar mekanizması.

    Yön seçimi: index[d] = queue_count[d] + lambda * excess_wait[d]
        (toplam beklemeyi minimize eden greedy-optimal "en büyük kuyruk" kuralı
        + adalet kısıtının Lagrange-tarzı fiyatlandırması), bir cycle-fairness
        katmanıyla sınırlanır: aynı turda henüz servis edilmemiş aktif bir yön
        varsa, index'e göre kazanan zaten servis edilmişse unserved yönler
        arasından en yüksek index'e sahip olan seçilir.
    Yeşil süresi: queue_count[d] / discharge_rate[d]
        ("kuyruğu gerçekten temizlemek için ne kadar gerekiyor", heuristik
        çarpan yığını değil), 2+ yön aktifken `multi_direction_max_green`
        tavanına clamp'lenir. `params.demand_share_scaling_exponent`
        (varsayılan 0.0 = kapalı, v1/v2 davranışı) >0 iken bu tavan sabit
        kalmaz: seçilen yönün o anki aktif toplam talep içindeki payı, eşit
        dağılım payından (1/aktif_yön_sayısı) ne kadar fazlaysa tavan o kadar
        yükselir (`base_cap * share_ratio^exponent`) -- böylece baskın bir
        kuyruk (ör. 20 araç), zayıf bir kuyrukla (ör. 1 araç) artık aynı sabit
        süreye sıkışmaz, ama dengeli senaryolarda (pay ~ eşit pay) davranış
        mevcut sabit tavanla aynı kalır. Adalet garantisi (sıralama, hangi
        yönün ne zaman gideceği) cycle-fairness'tan gelir, bu mekanizmadan
        etkilenmez -- yalnızca süre (ne kadar yeşil kalacağı) ölçekleniyor.
    Emergency: `params.emergency_priority_enabled` (varsayılan True) açıkken,
        ground truth'taki konum/hız verisiyle hesaplanan kesin ETA kadar yeşil
        verilir (sabit bir sabit değil). Gerekirse devam eden bir yeşil,
        controllers/adaptive_controller.py'deki opt-in `should_preempt`
        hook'u üzerinden ortasından kesilir (gerçek mid-phase preemption);
        emergency araç ZATEN yeşil olan yöndeyse ve faz süresi dolmak
        üzereyse, simetrik `get_green_extension` hook'u ile (güvenlik üst
        sınırına kadar) tutulur. `emergency_priority_enabled=False` iken
        emergency araçlar hiçbir özel muamele görmez -- state zaten tip
        ayrımı yapmadan tüm araçları saydığından (bkz. `ground_truth_provider`),
        emergency araçlar otomatik olarak normal kuyruk üyesi gibi işlenir.
        `emergency_starvation_override_limit` parametresi verilmişse (bkz.
        `is_starvation_guard_active`), emergency önceliği başka bir yön
        kritik derecede açken bir tur atlanır; parametre verilmemişse
        emergency koşulsuz öncelik alır.
    """

    strategy_key = "optimal_ground_truth"

    # Panel/debug: direction_debug'daki "score" alaninin nasil okunmasi
    # gerektigini belirtir -- burada index yuksek olan yon kazanir.
    score_semantics = {"label": "index (queue+λ·excess_wait)", "higher_is_better": True}

    DIRECTIONS = ["right", "down", "left", "up"]
    ACTIVE_LANES = [1, 2]

    def ensure_runtime_state(self, engine):
        if not hasattr(engine, "optimal_direction_runtime"):
            engine.optimal_direction_runtime = {
                direction: {"discharge_rate": 0.0}
                for direction in self.DIRECTIONS
            }

        if not hasattr(engine, "optimal_phase_tracking"):
            engine.optimal_phase_tracking = None

        if not hasattr(engine, "optimal_cycle_state"):
            engine.optimal_cycle_state = {"served_directions": set()}

        if not hasattr(engine, "optimal_hold_state"):
            engine.optimal_hold_state = {"direction": None, "total_extended": 0.0}

    def get_direction_crossed(self, engine, direction):
        try:
            return engine.vehicles[direction].get("crossed", 0)
        except Exception:
            return 0

    # --- Cycle-fairness: her aktif yönün bir turda en az bir kez servis
    # edilmesini garanti eden takip mekanizması. `mark_cycle_served`
    # BURADAN çağrılmaz -- adaptive_controller.py'nin select_and_prepare_phase()'i,
    # initial_selection/single_demand gibi override'lar sonrası KESİNLEŞEN
    # yönle bunu opt-in bir hook olarak çağırır (bkz. docs/strategy_structure.md).
    # Stratejinin kendi choose_next_phase() tahmini, controller tarafından
    # override edilebildiğinden burada işaretleme yapmak yanlış yönü
    # işaretleme riski taşırdı. ---

    def reset_cycle(self, engine):
        engine.optimal_cycle_state["served_directions"] = set()

    def mark_cycle_served(self, engine, direction):
        if direction is None:
            return
        engine.optimal_cycle_state["served_directions"].add(direction)

    def reset_cycle_if_completed(self, engine, active_directions):
        served = engine.optimal_cycle_state["served_directions"]
        if served and set(active_directions).issubset(served):
            self.reset_cycle(engine)

    def get_unserved_active_directions(self, engine, active_directions):
        served = engine.optimal_cycle_state["served_directions"]
        return [d for d in active_directions if d not in served]

    def distance_to_stop_line(self, engine, vehicle, direction):
        stop_line = engine.stopLines.get(direction)

        if stop_line is None:
            return None

        width = vehicle.image.get_rect().width
        height = vehicle.image.get_rect().height

        if direction == "right":
            return max(0.0, stop_line - (vehicle.x + width))
        if direction == "down":
            return max(0.0, stop_line - (vehicle.y + height))
        if direction == "left":
            return max(0.0, vehicle.x - stop_line)
        if direction == "up":
            return max(0.0, vehicle.y - stop_line)

        return None

    def vehicles_ahead_count(self, engine, vehicle):
        # Ayni serit icinde, bu aracin ONUNDE olan ve henuz kesisimi
        # gecmemis arac sayisi -- eta_seconds'un "onunde kimse yokmus gibi"
        # serbest-akis varsayimini duzeltmek icin (bkz. eta_seconds notu).
        lane_vehicles = engine.vehicles[vehicle.direction][vehicle.lane]
        return sum(
            1
            for other in lane_vehicles[:vehicle.index]
            if getattr(other, "crossed", 0) == 0
        )

    def eta_seconds(self, engine, vehicle, distance, params=None):
        # Bir aracın tick başına piksel hızı = base_speed * playback_speed;
        # bir tick'in temsil ettiği simüle saniye = (1/fps) * playback_speed.
        # ETA = distance / hız (tick) * saniye/tick = distance / (base_speed * fps)
        # -- playback_speed sadeleşiyor, ETA gerçek simüle saniye cinsinden kalır.
        #
        # NOT: bu saf "mesafe/hiz" hesabi, aracin ONUNDE kimse yokmus gibi
        # serbest akis varsayiyor. Acil durum araci onlarca aracin arkasina
        # sikismissa (GERCEKTE cok yakinsa bile), bu hesap ETA'yi ciddi
        # sekilde KUCUK gosteriyordu -- verilen yesil suresi aracin onundeki
        # kuyruk boşalmadan asla yetmiyor, bu da ayni aracin tur tur yeniden
        # secilip hic ilerlememesine yol aciyordu (kullanicinin GUI'de
        # gozlemledigi durum). Onunde servis edilmemis arac varsa, ETA'yi
        # o araclarin ogrenilen discharge_rate'e gore boşalma suresiyle de
        # karsilastirip BUYUK olani aliyoruz -- boylece verilen yesil suresi
        # "kuyruk hic yokmus gibi" degil, gercekci bir beklentiyi yansitir.
        base_speed = getattr(vehicle, "base_speed", None)
        fps = getattr(engine, "fps", None)

        if not base_speed or not fps:
            return None

        free_flow_eta = distance / (base_speed * fps)

        vehicles_ahead = self.vehicles_ahead_count(engine, vehicle)

        if vehicles_ahead <= 0:
            return free_flow_eta

        min_effective_discharge_rate = float((params or {}).get("min_effective_discharge_rate", 0.3))
        runtime = engine.optimal_direction_runtime.get(vehicle.direction, {})
        discharge_rate = max(runtime.get("discharge_rate", 0.0), min_effective_discharge_rate)
        queue_clear_eta = vehicles_ahead / discharge_rate

        return max(free_flow_eta, queue_clear_eta)

    def find_nearest_emergency_vehicle(self, engine, direction, require_waiting=True):
        best_vehicle = None
        best_distance = None

        for lane in self.ACTIVE_LANES:
            for vehicle in engine.vehicles[direction][lane]:
                if not getattr(vehicle, "isEmergency", False):
                    continue

                if getattr(vehicle, "crossed", 0) == 1:
                    continue

                # Henuz kuyruga hic yaklasmamis (serbestce ilerleyen) bir
                # acil durum araci icin oncelik vermeye GEREK yok -- zaten
                # engellenmeden ilerliyor. Oncelik, GERCEKTEN bloke oldugu
                # an (kirmizida kendi durma noktasinda ya da onundeki
                # bekleyen araca zincirlenmis) anlamli. Bu kontrol
                # olmadan, kavsaga yuzlerce piksel uzakta, daha kavsaga
                # yaklasmamis bir acil durum araci bile hemen normal
                # trafigin onune geciyordu.
                #
                # `require_waiting=False` is for the direction that is green
                # right now (get_green_extension): waitingDueToSignalQueue is
                # never set while a vehicle's own signal is green, so with the
                # flag required the hold could not find any vehicle at all.
                if require_waiting and not getattr(vehicle, "waitingDueToSignalQueue", False):
                    continue

                distance = self.distance_to_stop_line(engine, vehicle, direction)

                if distance is None:
                    continue

                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_vehicle = vehicle

        return best_vehicle, best_distance

    def find_priority_emergency(self, engine):
        best_direction = None
        best_vehicle = None
        best_distance = None

        for direction in self.DIRECTIONS:
            vehicle, distance = self.find_nearest_emergency_vehicle(engine, direction)

            if vehicle is None:
                continue

            if best_distance is None or distance < best_distance:
                best_direction = direction
                best_vehicle = vehicle
                best_distance = distance

        return best_direction, best_vehicle, best_distance

    def other_direction_severely_starving(self, engine, exclude_direction, hard_limit):
        # Bir emergency aracin ETA'si, kendi yonundeki normal trafik kuyruguna
        # sikismis olmasi yuzunden defalarca yeniden hesaplanip her seferinde
        # ayni yonu kazandirabiliyordu -- bu da o yon disindaki tum yonlerin
        # sinirsiz ac kalmasina yol aciyordu (bkz. mixed_master_scenario
        # dogrulama bulgusu: 'right' 200+ saniye boyunca hic servis alamadi).
        # Bu kontrol, emergency oncelik verilmeden once, gercekten "baska
        # bir yon kritik derecede ac mi" diye bakar. get_direction_max_stopped_wait
        # bos/talebi olmayan bir yon icin zaten 0.0 dondurdugunden, ayrica bir
        # "aktif yon mu" kontrolune gerek yok.
        for direction in self.DIRECTIONS:
            if direction == exclude_direction:
                continue
            if get_direction_max_stopped_wait(engine, direction) > hard_limit:
                return True
        return False

    def emergency_priority_enabled(self, params):
        return bool(params.get("emergency_priority_enabled", True))

    def is_starvation_guard_active(self, engine, exclude_direction, params):
        # `emergency_starvation_override_limit` artik opsiyonel: parametre
        # yoksa/None ise emergency oncelik kosulsuzdur (kullanicinin acik
        # talebi). Parametre verilmisse (ör. v1'in mevcut kaydinda 60.0),
        # eski "baska yon kritik ac mi" korumasi aynen calismaya devam eder
        # -- bu sayede v1'in tarihsel/belgelenen davranisi degismez, yeni
        # versiyonlar sadece bu parametreyi params'tan cikararak kosulsuz
        # onceliğe gecebilir.
        starvation_limit = params.get("emergency_starvation_override_limit")

        if starvation_limit is None:
            return False

        return self.other_direction_severely_starving(
            engine, exclude_direction, float(starvation_limit)
        )

    def should_preempt(self, engine, params, current_direction, elapsed_green_seconds):
        if not self.emergency_priority_enabled(params):
            return False

        min_green = int(params.get("min_green", 5))

        # Güvenlik kısıtı: kendi min_green tabanını doldurmamış bir yeşil
        # asla kesilmez (gerçek preemption sistemlerindeki "minimum green
        # guarantee" kuralı).
        if elapsed_green_seconds < min_green:
            return False

        emergency_direction, emergency_vehicle, emergency_distance = self.find_priority_emergency(engine)

        if emergency_direction is None or emergency_direction == current_direction:
            return False

        if self.is_starvation_guard_active(engine, emergency_direction, params):
            return False

        if not self.is_emergency_reachable_within_budget(
            engine, emergency_vehicle, emergency_distance, params
        ):
            return False

        return True

    def is_emergency_reachable_within_budget(self, engine, vehicle, distance, params):
        # Bir acil durum araci "waitingDueToSignalQueue" oldugu icin (yani
        # GERCEKTEN durmus/zincirli) teknik olarak "bloke" sayilabilir, ama
        # kendi yonundeki UZUN bir kuyrugun en arkasinda, kavsaga hala
        # yuzlerce piksel uzakta olabilir. Bu durumda oncelik verilse bile,
        # sistemin verebilecegi en uzun sure (max_green + emergency_max_hold_time)
        # icinde bu arac onundeki kuyruk bosalip kesisimi GERCEKTEN gecemeyebilir
        # -- bu da "oncelik verilen yon" ile "gecen arac" arasinda kopukluk
        # yaratir: diger yonler bosuna acil-oncelik bekler, arac yine de
        # gecmez, bir sonraki tur AYNI arac icin ayni sey tekrarlanir.
        # Bu kontrol, oncelik SADECE aracin bu butce icinde gercekten
        # gecebilecegi kadar yakinlastigi an verilsin diye eklendi -- ETA
        # kuyruk normal cycling ile kucaldikce (ya da arac fiilen yaklastikca)
        # bir sonraki karar turunda tekrar degerlendirilir, arac unutulmaz.
        eta = self.eta_seconds(engine, vehicle, distance, params)

        if eta is None:
            return True

        max_green = int(params.get("max_green", 30))
        max_hold_time = float(params.get("emergency_max_hold_time", 20.0))
        clearance_buffer = float(params.get("emergency_clearance_buffer", 2.0))
        max_feasible_wait = max_green + max_hold_time

        return (eta + clearance_buffer) <= max_feasible_wait

    def get_green_extension(self, engine, params, current_direction, remaining_green):
        if not self.emergency_priority_enabled(params):
            return 0

        self.ensure_runtime_state(engine)

        # Sadece faz gerçekten bitmek üzereyken değerlendir; her tick
        # gereksiz uzatma denemesi yapma.
        extension_check_threshold = float(params.get("emergency_extension_check_threshold", 2.0))
        if remaining_green > extension_check_threshold:
            return 0

        vehicle, distance = self.find_nearest_emergency_vehicle(
            engine, current_direction, require_waiting=False
        )
        if vehicle is None:
            return 0

        hold_state = engine.optimal_hold_state
        max_hold = float(params.get("emergency_max_hold_time", 20.0))

        if hold_state["direction"] != current_direction:
            hold_state["direction"] = current_direction
            hold_state["total_extended"] = 0.0

        remaining_hold_budget = max_hold - hold_state["total_extended"]
        if remaining_hold_budget <= 0:
            return 0

        eta = self.eta_seconds(engine, vehicle, distance, params)
        if eta is None:
            return 0

        clearance_buffer = float(params.get("emergency_clearance_buffer", 2.0))
        needed = (eta + clearance_buffer) - remaining_green

        if needed <= 0:
            return 0

        # Holding the green only helps if the vehicle can actually clear the
        # intersection within what is left of the hold budget. Otherwise the
        # cross traffic waits and the vehicle still gets stopped.
        if needed > remaining_hold_budget:
            return 0

        extension = min(needed, remaining_hold_budget)
        extension = max(0, round(extension))

        if extension <= 0:
            return 0

        hold_state["total_extended"] += extension

        vehicle.receivedEmergencyHold = True
        vehicle.totalEmergencyHoldTime += extension

        return int(extension)

    def choose_next_phase(self, state, params, engine):
        self.ensure_runtime_state(engine)

        emergency_result = self.choose_emergency_phase(params, engine)

        if emergency_result is not None:
            return emergency_result

        return self.choose_normal_phase(state, params, engine)

    def choose_emergency_phase(self, params, engine):
        # --- Emergency: ground-truth ETA'sına göre kesin süre, sabit yok ---
        # None dönerse "bu karar turunda emergency oncelik yok" demektir --
        # cagiran, normal trafik mantigina devam eder. Bu metod
        # RollingHorizonGroundTruthStrategy tarafindan da degistirilmeden
        # miras alinir; emergency kisa-devresi tum stratejilerde ayni.
        min_green = int(params.get("min_green", 5))
        max_green = int(params.get("max_green", 30))
        emergency_clearance_buffer = float(params.get("emergency_clearance_buffer", 2.0))

        emergency_direction, emergency_vehicle, emergency_distance = (
            self.find_priority_emergency(engine)
            if self.emergency_priority_enabled(params)
            else (None, None, None)
        )

        if emergency_direction is not None:
            if self.is_starvation_guard_active(engine, emergency_direction, params):
                # Emergency aracin kendi yonundeki kuyruga sikisip yavas
                # ilerlemesi, her karar turunda ayni yonu kazandirip diger
                # yonleri sinirsiz ac birakabiliyordu (bkz. mixed_master_scenario
                # dogrulamasi: 'right' emergency arac 'down'da sikisirken 200+
                # saniye hic servis alamadi). `emergency_starvation_override_limit`
                # parametresi verilmisse (bkz. is_starvation_guard_active) baska
                # bir yon zaten bu kadar acsa, emergency oncelik BU TEK karar
                # turu icin atlanir -- asagidaki normal adalet mantigi
                # excess_wait'i zaten skora dahil ettigi icin ac kalan yonu
                # dogal olarak secer. Emergency arac unutulmuyor: bir sonraki
                # karar turunde tekrar degerlendirilir. Parametre verilmemisse
                # (yeni versiyonlarin varsayilani) bu koruma hic devreye girmez
                # -- emergency kosulsuz oncelik alir.
                emergency_direction = None

        if emergency_direction is not None and not self.is_emergency_reachable_within_budget(
            engine, emergency_vehicle, emergency_distance, params
        ):
            # Arac su an icin kavsaga cok uzak / onunde cok fazla kuyruk var
            # -- bkz. is_emergency_reachable_within_budget yorumu. Bu turda
            # oncelik verilmez, normal trafik mantigi devam eder; arac
            # yaklastikca (ETA kucaldikce) bir sonraki turda tekrar
            # degerlendirilecek.
            emergency_direction = None

        if emergency_direction is None:
            return None

        eta = self.eta_seconds(engine, emergency_vehicle, emergency_distance, params)

        if eta is None:
            green_time = min_green
        else:
            green_time = int(max(min_green, min(max_green, round(eta + emergency_clearance_buffer))))

        engine.optimal_phase_tracking = {
            "direction": emergency_direction,
            "green_time": green_time,
            "crossed_before": self.get_direction_crossed(engine, emergency_direction),
        }

        reason = (
            f"{emergency_direction.upper()} selected by Optimal Ground-Truth Strategy: "
            f"emergency vehicle detected (type={emergency_vehicle.emergencyType}), "
            f"distance={emergency_distance:.1f}px, "
            f"eta={'n/a' if eta is None else f'{eta:.1f}s'}, "
            f"green_time=eta+clearance_buffer({emergency_clearance_buffer}s)={green_time}s. "
            f"Ground truth'un konum/hız verisiyle hesaplanan kesin süre, sabit bir "
            f"deger degil."
        )

        return (
            emergency_direction,
            green_time,
            reason,
            {
                "emergency_priority": True,
                "direction_debug": self.build_simple_direction_debug(
                    engine, emergency_direction, emergency_direction=emergency_direction
                ),
                "score_semantics": self.score_semantics,
            },
        )

    def build_simple_direction_debug(self, engine, chosen_direction, emergency_direction=None):
        # decision_meta'nin "direction_debug" alani icin, index/discharge_rate
        # gibi normal-karar-ozgu verinin anlamli olmadigi durumlarda (emergency
        # kisa-devresi, ya da hic aktif talep yokken) kullanilan basit/ortak
        # bir kesit -- panel bu durumlarda da cokmesin diye ayni sekli tasir.
        served = engine.optimal_cycle_state.get("served_directions", set())

        return {
            direction: {
                "queue": self.count_direction_queue(engine, direction),
                "active": self.count_direction_queue(engine, direction) > 0,
                "index": None,
                "excess_wait": None,
                "discharge_rate": None,
                "served_this_cycle": direction in served,
                "chosen": direction == chosen_direction,
                "emergency": direction == emergency_direction,
            }
            for direction in self.DIRECTIONS
        }

    def count_direction_queue(self, engine, direction):
        return sum(
            1
            for lane in self.ACTIVE_LANES
            for vehicle in engine.vehicles[direction][lane]
            if getattr(vehicle, "crossed", 0) == 0
        )

    def choose_normal_phase(self, state, params, engine):
        min_green = int(params.get("min_green", 5))
        max_green = int(params.get("max_green", 30))
        fairness_lambda = float(params.get("fairness_lambda", 1.5))
        starvation_soft_limit = float(params.get("starvation_soft_limit", 20))
        min_effective_discharge_rate = float(params.get("min_effective_discharge_rate", 0.3))
        multi_direction_max_green = float(params.get("multi_direction_max_green", 15))
        demand_share_scaling_exponent = float(params.get("demand_share_scaling_exponent", 0.0))

        # --- Normal trafik: kısıtlı optimizasyon (c-mu kurali + adalet kisiti) ---
        current_direction = engine.directionNumbers.get(engine.controller.currentGreen, None)

        queue_counts = {d: float(state.get(d, 0)) for d in self.DIRECTIONS}
        active_directions = [d for d in self.DIRECTIONS if queue_counts[d] > 0]

        if not active_directions:
            fallback_direction = current_direction or self.DIRECTIONS[0]

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

        self.reset_cycle_if_completed(engine, active_directions)

        indices = {}
        excess_waits = {}

        for direction in active_directions:
            max_wait = get_direction_max_stopped_wait(engine, direction)
            excess_wait = max(0.0, max_wait - starvation_soft_limit)
            excess_waits[direction] = excess_wait
            indices[direction] = queue_counts[direction] + fairness_lambda * excess_wait

        raw_best_direction = max(active_directions, key=lambda d: indices[d])

        cycle_fairness_enabled = bool(params.get("cycle_fairness_enabled", True))
        unserved_directions = (
            self.get_unserved_active_directions(engine, active_directions)
            if cycle_fairness_enabled
            else []
        )
        cycle_note = ""

        # Kullanıcının açık talebi: bir cycle içinde talebi olan HER yöne,
        # ne kadar beklemiş olursa olsun, tekrar sırası gelmeden aynı yön
        # ikinci kez yeşil olmasın (round-robin garantisi). Bu yüzden
        # "eligible" burada saf demand>0 + henüz servis edilmemiş anlamına
        # gelir; ek bir minimum-bekleme eşiği yok -- öyle bir eşik, az önce
        # kuyruğa giren bir yönü "henüz hak etmedi" diye atlayıp tam olarak
        # kullanıcının şikayet ettiği "aynı yol üst üste yeşil alıyor"
        # davranışını üretiyordu. `params.cycle_fairness_enabled=False` iken
        # bu garanti tamamen devre dışı -- yön seçimi saf index'e göre yapılır.
        if unserved_directions and raw_best_direction not in unserved_directions:
            best_direction = max(unserved_directions, key=lambda d: indices[d])
            cycle_note = (
                f" Cycle-fairness: {raw_best_direction.upper()} already served this "
                f"cycle, redirected to unserved {best_direction.upper()}."
            )
        else:
            best_direction = raw_best_direction

        runtime = engine.optimal_direction_runtime[best_direction]
        discharge_rate = max(runtime["discharge_rate"], min_effective_discharge_rate)

        raw_green = queue_counts[best_direction] / discharge_rate

        # Birden fazla yön aktif talep taşıyorken, "kuyruğu tam temizlemeye
        # yetecek süre" fikri tek başına yanıltıcı: best_direction yeşilken
        # DİĞER TÜM yönler o sürede kesinlikle sıfır throughput üretiyor.
        # Tek bir aktif yön varsa (controller zaten bunu ayrı bir guard ile
        # ele alıyor) tam max_green'e izin verilir; 2+ aktif yön varsa daha
        # sıkı bir üst sınır (multi_direction_max_green) kullanılır.
        share_ratio = 1.0

        if len(active_directions) <= 1:
            effective_max_green = max_green
        else:
            base_cap = min(max_green, multi_direction_max_green)

            if demand_share_scaling_exponent > 0:
                # Sabit bir tavan, 1 araçlık kuyruk ile 20 araçlık kuyruğa
                # neredeyse aynı süreyi veriyordu (raw_green her ikisinde de
                # tavanı asiyor). Bunun yerine tavanı, secilen yonun O ANKI
                # aktif taleplerin icindeki PAYINA gore olcekliyoruz: pay
                # esit-dagilim payindan (1/aktif_yon_sayisi) ne kadar
                # fazlaysa tavan o kadar yukseliyor. Dengeli senaryolarda
                # (pay ~ esit pay) share_ratio ~ 1, davranis mevcut sabit
                # tavanla ayni kaliyor -- orasi zaten olculmus en iyi nokta.
                total_active_demand = sum(queue_counts[d] for d in active_directions)
                even_share = 1.0 / len(active_directions)

                if total_active_demand > 0:
                    demand_share = queue_counts[best_direction] / total_active_demand
                    share_ratio = demand_share / even_share

                effective_max_green = min(
                    max_green,
                    base_cap * (share_ratio ** demand_share_scaling_exponent),
                )
            else:
                effective_max_green = base_cap

        green_time = int(max(min_green, min(effective_max_green, round(raw_green))))

        engine.optimal_phase_tracking = {
            "direction": best_direction,
            "green_time": green_time,
            "crossed_before": self.get_direction_crossed(engine, best_direction),
        }

        scaling_note = (
            f" demand_share_ratio={share_ratio:.2f} (exponent={demand_share_scaling_exponent:.2f})."
            if demand_share_scaling_exponent > 0 and len(active_directions) > 1
            else ""
        )

        reason = (
            f"{best_direction.upper()} selected by Optimal Ground-Truth Strategy. "
            f"index={indices[best_direction]:.2f} "
            f"(queue={queue_counts[best_direction]:.0f}, "
            f"excess_wait={excess_waits[best_direction]:.1f}s, "
            f"fairness_lambda={fairness_lambda:.2f}), "
            f"discharge_rate={discharge_rate:.2f} veh/s, "
            f"raw_green=queue/discharge_rate={raw_green:.1f}s, "
            f"green_time={green_time}s (clamped to [{min_green},{int(effective_max_green)}])."
            f"{scaling_note}"
            f"{cycle_note}"
        )

        served_before_this_pick = set(engine.optimal_cycle_state.get("served_directions", set()))

        direction_debug = {
            direction: {
                "queue": queue_counts[direction],
                "active": direction in active_directions,
                "score": round(indices[direction], 2) if direction in indices else None,
                "excess_wait": round(excess_waits[direction], 1) if direction in excess_waits else None,
                "discharge_rate": round(
                    max(
                        engine.optimal_direction_runtime[direction]["discharge_rate"],
                        min_effective_discharge_rate,
                    ),
                    2,
                ),
                "served_this_cycle": direction in served_before_this_pick,
                "chosen": direction == best_direction,
                "emergency": False,
            }
            for direction in self.DIRECTIONS
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

    def preview_next_direction(self, engine, params):
        # SADECE panel/UI icin: "faz simdi bitseydi hangi yon secilirdi"
        # sorusunun READ-ONLY tahmini. choose_next_phase/choose_normal_phase
        # ile KARISTIRILMAMALI -- onlar engine.optimal_phase_tracking'i
        # yazar (discharge_rate ogrenimi buna dayanir), bu yuzden panel
        # her frame'de gercek karar metodlarini "onizleme" amacli cagiramaz
        # (cagirirsa her frame'de tracking'i ezip discharge_rate ogrenimini
        # bozar). Bu metod hicbir engine/strateji durumuna yazmaz.
        # Rolling-horizon aileleri bunu override ETMEZ -- coklu-adim aramanin
        # tek-adimlik (myopic) bir yaklasik tahmini kullanilir, bir rozet
        # icin yeterince dogru.
        self.ensure_runtime_state(engine)
        current_direction = engine.directionNumbers.get(engine.controller.currentGreen, None)

        if self.emergency_priority_enabled(params):
            emergency_direction, emergency_vehicle, emergency_distance = self.find_priority_emergency(engine)

            if (
                emergency_direction is not None
                and emergency_direction != current_direction
                and not self.is_starvation_guard_active(engine, emergency_direction, params)
                and self.is_emergency_reachable_within_budget(
                    engine, emergency_vehicle, emergency_distance, params
                )
            ):
                return emergency_direction

        state = engine.controller.state_provider.get_state()
        queue_counts = {d: float(state.get(d, 0)) for d in self.DIRECTIONS}
        active_directions = [d for d in self.DIRECTIONS if queue_counts[d] > 0]

        if not active_directions:
            return None

        starvation_soft_limit = float(params.get("starvation_soft_limit", 20))
        fairness_lambda = float(params.get("fairness_lambda", 1.5))

        indices = {}
        for direction in active_directions:
            max_wait = get_direction_max_stopped_wait(engine, direction)
            excess_wait = max(0.0, max_wait - starvation_soft_limit)
            indices[direction] = queue_counts[direction] + fairness_lambda * excess_wait

        raw_best_direction = max(active_directions, key=lambda d: indices[d])

        if not bool(params.get("cycle_fairness_enabled", True)):
            return raw_best_direction

        served = set(engine.optimal_cycle_state.get("served_directions", set()))
        if served and set(active_directions).issubset(served):
            served = set()

        unserved_directions = [d for d in active_directions if d not in served]

        if unserved_directions and raw_best_direction not in unserved_directions:
            return max(unserved_directions, key=lambda d: indices[d])

        return raw_best_direction

    def update_discharge_after_phase(self, engine, alpha=0.35):
        self.ensure_runtime_state(engine)

        tracking = getattr(engine, "optimal_phase_tracking", None)

        if not tracking:
            return

        direction = tracking["direction"]
        green_time = max(1, tracking["green_time"])
        crossed_before = tracking["crossed_before"]
        crossed_after = self.get_direction_crossed(engine, direction)

        released = max(0, crossed_after - crossed_before)
        rate = released / green_time

        runtime = engine.optimal_direction_runtime[direction]
        runtime["discharge_rate"] = (
            alpha * rate + (1 - alpha) * runtime["discharge_rate"]
        )

        engine.optimal_phase_tracking = None
