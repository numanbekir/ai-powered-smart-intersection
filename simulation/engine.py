import copy
import math
import random
import threading
import time

import pygame

from controllers.adaptive_controller import AdaptiveSignalController
from controllers.fixed_time_controller import FixedTimeSignalController
from core.paths import IMAGES_DIR
from simulation.decision_logger import DecisionLogger
from simulation.metrics import summarize_direction
from simulation.vehicle import Vehicle
from state_providers.ground_truth_provider import GroundTruthStateProvider
from state_providers.yolo_provider import YoloStateProvider


class SimulationEngine:
    ACTIVE_LANES = [1, 2]

    # Sim gorunumundeki isik etiketleri ile kontrol panelindeki (hero)
    # etiketlerin AYNI olmasi icin tek, paylasilan kaynak -- hangi fiziksel
    # isigin hangi mantiksal yone ait oldugu konusunda karisiklik olmasin.
    #
    # NOT: bu degerler artik aracin hareket yonune gore degil, isigin
    # EKRANDAKI FIZIKSEL KONUMUNA gore etiketleniyor.
    # Ic anahtarlar ("right"/"down"/"left"/"up") aracin hareket yonunu
    # temsil etmeye devam ediyor -- degismedi, hicbir strateji/test/
    # scenario JSON'u bundan etkilenmiyor, SADECE bu sozlugun DEGERLERI
    # (ekranda gosterilen metin) degisti. Geometrik dogrulama
    # (__init__'teki stopLines/signalCoods koordinatlarindan): "right"
    # (saga/dogu yonune hareket eden araclar) isigi fiziksel olarak
    # ekranin SOL-ALT bolgesinde; "left" isigi SAG-UST'te; "down" (asagi
    # hareket) isigi UST-SOL'da; "up" isigi ALT-SAG'da -- yani her isik,
    # aracin hareket yonunun TAM TERSI konumda (arac o yone GIDIYOR,
    # isik/kuyruk ise GELDIGI kenarda duruyor). Bu yuzden konum-bazli
    # etiket, hareket-yonu etiketinin caprazi: right<->left, down<->up.
    SIGNAL_LABELS = {"right": "SOL", "down": "YUKARI", "left": "SAĞ", "up": "AŞAĞI"}

    # __init__ imzası
    def __init__(
        self,
        scenario,
        test_name,
        controller_mode,
        controller_version=None,
        state_provider_id="ground_truth_v1",
        headless=False,
    ):
        self.scenario = copy.deepcopy(scenario)
        self.config = copy.deepcopy(scenario["config"])
        self.test_name = test_name
        self.controller_mode = controller_mode
        self.controller_version = copy.deepcopy(controller_version)
        self.state_provider_id = state_provider_id
        self.headless = headless

        self.random_seed = int(self.config.get("random_seed", 42))
        random.seed(self.random_seed)

        self.images_dir = IMAGES_DIR
        self.fps = int(self.config["fps"])
        self.simulation_time = float(self.config["simulation_time"])
        # Vehicles spawned before this many simulated seconds are excluded
        # from wait/delay/queue statistics (the run starts from an empty
        # intersection). 0 keeps every vehicle, as before.
        self.warmup_time = float(self.config.get("warmup_time", 0.0))
        self.playback_speed = max(0.1, float(self.config["playback_speed"]))
        self.fixed_config = copy.deepcopy(self.config["fixed"])

        self.noOfSignals = 4
        self.simulationRunning = True
        self.paused = False
        self.request_restart = False
        self.request_stop = False

        self.speeds = self.config["vehicle_speeds"]
        self.emergency_config = self.config.get("emergency", {})
        self.emergency_vehicle_types = ["ambulance", "police", "firetruck"]
        self.last_emergency_spawn_time = -999999.0
        self.emergency_spawned_count = 0

        self.x = {
            "right": [0, 0, 0],
            "down": [0, 415, 384],
            "left": [0, 900, 900],
            "up": [0, 458, 492],
        }

        self.y = {
            "right": [0, 451, 478],
            "down": [0, 0, 0],
            "left": [0, 424, 397],
            "up": [0, 900, 900],
        }

        self.vehicles = {
            direction: {1: [], 2: [], "crossed": 0}
            for direction in ["right", "down", "left", "up"]
        }

        self.directionNumbers = {
            0: "right",
            1: "down",
            2: "left",
            3: "up",
        }

        self.directionToNumber = {
            "right": 0,
            "down": 1,
            "left": 2,
            "up": 3,
        }

        self.signalCoods = [
            {"pos": (315, 540), "angle": 270},
            {"pos": (345, 332), "angle": 180},
            {"pos": (585, 360), "angle": 90},
            {"pos": (558, 565), "angle": 0},
        ]

        self.signalTimerCoods = [
            (250, 530),
            (335, 260),
            (635, 350),
            (547, 615),
        ]

        self.stopLines = {
            "right": 350,
            "down": 370,
            "left": 550,
            "up": 535,
        }

        self.defaultStop = {
            "right": 340,
            "down": 360,
            "left": 560,
            "up": 545,
        }

        self.stoppingGap = 25
        self.movingGap = 215
        self.rotationAngle = 3

        # Gercek kavsak kayitlarindan olculen ortalama start-up lost time
        # (data/real_world_calibration.csv, tools/real_world_calibration_analysis.py):
        # bir arac yesil yandiginda aninda degil, ~3s'lik bir reaksiyon
        # gecikmesinden sonra hareket etmeye baslar.
        self.startupLostTime = 3.0

        self.turnTriggerPoints = {
            "right": {"left": 475, "right": 400},
            "down": {"left": 480, "right": 408},
            "left": {"left": 430, "right": 510},
            "up": {"left": 440, "right": 490},
        }

        self.allowedVehicleTypes = self.config["allowed_vehicle_types"]

        self.vehiclesTurned = {
            direction: {1: [], 2: []}
            for direction in ["right", "down", "left", "up"]
        }

        self.vehiclesNotTurned = {
            direction: {1: [], 2: []}
            for direction in ["right", "down", "left", "up"]
        }

        self.vehicleMetrics = {
            direction: []
            for direction in ["right", "down", "left", "up"]
        }

        self.emergencyVehicleMetrics = {
            "wait_times": [],
            "crossed": 0,
            "spawned": 0,

            "hold_count": 0,
            "total_hold_time": 0.0,
            "hold_success_count": 0,
            "hold_max_time": 0.0,
        }

        self.emergency_priority_metrics = {
            "priority_activation_count": 0,
        }

        self.normalVehicleMetrics = {
            "wait_times": [],
            "crossed": 0,
        }

        # Control delay of every measured vehicle that crossed (see
        # Vehicle.control_delay).
        self.vehicleDelays = []

        self.queue_samples = {
            direction: []
            for direction in ["right", "down", "left", "up"]
        }
        self.queue_samples["total"] = []

        self.queue_peak = {
            direction: 0
            for direction in ["right", "down", "left", "up"]
        }
        self.queue_peak["total"] = 0

        self.direction_last_served_at = {
            direction: 0.0
            for direction in ["right", "down", "left", "up"]
        }

        self.decision_logger = DecisionLogger()
        self.simulation_elapsed = 0.0
        self._tick_condition = threading.Condition()
        self._worker_threads = []
        self._worker_sleep_target = {}

        self.base_simulation_delta = 1.0 / self.fps
        self.current_simulation_delta = (
            self.base_simulation_delta * self.playback_speed
        )

        self.phase_performance_history = []

        # Cycle-fairness kompasi: GORSEL olarak yanan yonler
        # (cycle_served_directions), stratejinin kendi optimal_cycle_state'ini
        # dogrudan aynalamiyor -- kendi 2 saniyelik "tur tamamlandi" gorsel
        # penceresi var (bkz. update_cycle_compass_state).
        self.cycle_served_directions = set()
        self._cycle_prev_real_served = set()
        self._cycle_carryover = set()
        # Sadece fallback yolunda (cycle-fairness'i olmayan varsayimsal bir
        # strateji / fixed mod) kullanilir.
        self.previous_green_direction_for_cycle = None

        self.cycle_completed_flash_until = 0.0
        self.cycle_completed_pending_reset = False
        self.completed_cycle_count = 0

        # Recent-green-phases panel: her tamamlanan yesil fazin gercek
        # suresini ve o faz sirasinda kesisimi GECEN arac sayisini tutar.
        # (Onceden var olan v8_metrics/phase_performance_history/
        # register_v8_phase_metrics hicbir yerden cagrilmiyordu -- tamamen
        # olu kod. Bu, batch/collect_results semasina dokunmadan, sadece
        # GUI paneli icin ayri/minimal bir mekanizma.)
        self.active_phase_tracking = None
        self.recent_phase_history = []

        # Terminal-log paneli: kac satir asagi kaydirildigi (0 = en yeniyi
        # gosteriyor) ve fare tekerlegi olaylarinin hangi ekran dikdortgenine
        # isabet ettigini kontrol edebilmek icin son cizilen kutu (bkz.
        # run()'daki MOUSEWHEEL islenmesi).
        self.recent_phases_scroll_offset = 0
        self._recent_phases_log_rect = None

        # "What the strategy is thinking" da ayni terminal-log deseniyle:
        # her GERCEK karar (phase_change/initial_selection) icin bir log
        # kaydi -- bkz. log_adaptive_decision'daki cagri.
        self.decision_narrative_log = []
        self.narrative_scroll_offset = 0
        self._narrative_log_rect = None

        self.latest_decision_context = {
            "selected_direction": "-",
            "next_green": "-",
            "reason_full": "",
            "mode": "-",
        }

        self.v8_metrics = {
            "phase_extensions": 0,
            "early_cutoffs": 0,
            "avg_discharge_rate_samples": [],
            "avg_roi_samples": [],
            "wasted_green_time": 0.0,
            "effective_green_time": 0.0,
        }

        pygame.init()
        self.simulation = pygame.sprite.Group()
        # Called once per tick from the main loop, after vehicles have moved.
        # Read-only observers (dataset capture, evaluation) register here.
        self.tick_listeners = []

        self.state_provider = self.build_state_provider()
        self.controller = self.build_controller()

    def build_state_provider(self):
        if self.state_provider_id.startswith("ground_truth"):
            return GroundTruthStateProvider(self)

        if self.state_provider_id.startswith("yolo"):
            return YoloStateProvider(self)

        raise ValueError(f"Unknown state provider id: {self.state_provider_id}")

    def build_controller(self):
        if self.controller_mode == "fixed":
            return FixedTimeSignalController(self)

        if self.controller_mode == "adaptive":
            if not self.controller_version:
                raise ValueError("Adaptive controller requires version info.")

            return AdaptiveSignalController(
                self,
                self.state_provider,
                self.controller_version,
            )

        raise ValueError("controller_mode must be fixed or adaptive")

    def wait_if_paused(self):
        while self.paused and self.simulationRunning:
            time.sleep(0.05)

    def scaled_sleep(self, seconds):
        # `seconds` burada simüle edilmiş saniye anlamına gelir. Eskiden bu
        # metod gerçek wall-clock zamanında uyuyordu ve "1 simüle saniye"nin
        # gerçekte ne kadar sürdüğünü, ana döngünün gerçekten `fps` hızında
        # çalıştığını varsayarak tahmin ediyordu. Ana döngü yavaşladığında
        # (ör. çok araç birikince) bu varsayım bozulup controller/spawner
        # thread'lerinin simüle zamanı ana döngüden farklı ilerletmesine,
        # dolayısıyla aynı seed'in farklı sonuç üretmesine yol açıyordu.
        # Artık bu metod, ana döngünün `advance_simulation_time()` ile
        # ilerlettiği tek otoriter `simulation_elapsed` değerine ulaşılmasını
        # bekliyor; böylece controller/spawner'ın "zamanı", gerçek dünya
        # zamanlamasından bağımsız olarak ana döngüyle birebir örtüşüyor.
        #
        # The thread registers its wake-up time and is woken by the main loop
        # (advance_simulation_time removes the entry). While the entry exists
        # the thread counts as asleep, which is what wait_for_workers checks.
        ident = threading.get_ident()

        with self._tick_condition:
            self._worker_sleep_target[ident] = self.simulation_elapsed + seconds
            self._tick_condition.notify_all()

            while ident in self._worker_sleep_target and self.simulationRunning:
                self._tick_condition.wait(timeout=0.05)

            self._worker_sleep_target.pop(ident, None)

    def advance_simulation_time(self):
        with self._tick_condition:
            self.simulation_elapsed += self.current_simulation_delta

            for ident, target in list(self._worker_sleep_target.items()):
                if self.simulation_elapsed >= target:
                    del self._worker_sleep_target[ident]

            self._tick_condition.notify_all()
            self._wait_for_workers_locked()

    def wait_for_workers(self):
        with self._tick_condition:
            self._wait_for_workers_locked()

    def _wait_for_workers_locked(self):
        # A tick must not start while the controller or the spawner is still
        # reacting to the previous one. Without this the main loop only gave
        # them one frame of real time (1/fps) to finish, so under CPU load a
        # new vehicle or a signal change could land one tick late and the same
        # seed produced slightly different results.
        while self.simulationRunning and any(
            thread.is_alive() and thread.ident not in self._worker_sleep_target
            for thread in self._worker_threads
        ):
            self._tick_condition.wait(timeout=0.05)

    def stop_simulation(self):
        self.simulationRunning = False
        with self._tick_condition:
            self._tick_condition.notify_all()

    def _join_worker_threads(self, *threads, timeout=2.0):
        # Controller/spawner thread'leri (daemon=True) `simulationRunning`
        # bayragini kontrol ederek kendiliklerinden cikar, ama bunu ne zaman
        # farkedeceklerinin (ornegin scaled_sleep icindeki wait(timeout))
        # garantisi yok. `pygame.quit()` ana thread'de calisirken, spawner
        # thread hala `load_vehicle_image` icinde pygame.image.load/convert_alpha
        # gibi SDL cagrilari yapiyor olabilir -- bu, SDL'in ayni anda hem
        # yikilip hem baska bir thread'den kullanilmasi demek, ki bu segfault'a
        # yol aciyordu (birkac calistirma sonra "New/Edit Scenario" penceresi
        # acilirken gozlemlendi -- onceki kosunun spawner thread'i hala SDL'e
        # dokunurken pygame.quit() calismis, sonraki Tk islemleri bu bozuk
        # durumun ustune denk gelmis). pygame.quit()'ten ONCE thread'lerin
        # gercekten bittigini dogrulamak bu yarisi ortadan kaldirir.
        for thread in threads:
            if thread is not None and thread.is_alive():
                thread.join(timeout=timeout)

    def get_current_simulation_time(self):
        return round(self.simulation_elapsed, 2)

    def prepare_simulation_step(self):
        self.wait_for_workers()

        self.current_simulation_delta = (
            self.base_simulation_delta * self.playback_speed
        )

        return self.current_simulation_delta

    def get_current_direction_average_wait(self, direction):
        waits = self.vehicleMetrics[direction]
        return sum(waits) / len(waits) if waits else 0.0

    def get_direction_starvation_score(self, direction):
        return max(
            0.0,
            self.simulation_elapsed - self.direction_last_served_at[direction],
        )

    def mark_direction_served(self, direction):
        self.direction_last_served_at[direction] = self.simulation_elapsed

    def get_current_green_direction(self):
        return self.directionNumbers.get(self.controller.currentGreen, "-")

    def get_latest_direction_debug(self):
        # Onceden burada strateji mantigiyla hicbir ilgisi olmayan, engine'de
        # hardcode edilmis genel bir formul vardi (queue*1.0 + max_wait*0.35 +
        # emergency*100) -- v3'un gercek index'i veya RH'nin gercek projected
        # cost'uyla hicbir iliskisi yoktu, panelde "ne ise yaradigi belirsiz"
        # bir grafik ciziyordu. Artik stratejinin KENDI hesapladigi, gercek
        # karar verisini (decision_meta["direction_debug"], bkz.
        # controllers/strategies/{optimal_ground_truth,rolling_horizon_ground_truth}
        # _strategy.py) dogrudan gosteriyoruz.
        if self.controller_mode != "adaptive":
            return None

        return self.latest_decision_context.get("direction_debug")

    def get_latest_score_semantics(self):
        return self.latest_decision_context.get(
            "score_semantics",
            {"label": "score", "higher_is_better": True},
        )

    def build_decision_narrative(self):
        # WHY kutusu icin -- stratejinin URETTIGI teknik `reason` string'i
        # (queue=5, discharge_rate=0.44 gibi ham degiskenler) yerine, o
        # verinin YORUMLANMIS, gunluk dile cevrilmis hali. Ham deger dump'i
        # decision_log'da (batch/analiz icin) aynen kalmaya devam ediyor --
        # bu yalnizca panelin GORSEL sunumu.
        labels = self.SIGNAL_LABELS

        if self.controller_mode != "adaptive":
            return ["Sabit süreli döngü: her yön eşit ve değişmeyen bir yeşil süresi alır -- hiçbir şey ölçülmüyor/karar verilmiyor."]

        context = self.latest_decision_context
        mode = context.get("mode", "-")
        reason_full = context.get("reason_full") or ""
        selected = context.get("selected_direction")

        if mode in ("emergency_priority", "emergency_hold_priority"):
            selected_label = labels.get(selected, (selected or "-").upper())
            lines = [f"{selected_label} yönünde bir acil durum aracı var, bu yüzden normal trafiğin önüne geçiyor."]
            if "extended" in reason_full or "hold" in reason_full.lower():
                lines.append("Kavşağı geçebilmesi için yeşili biraz daha uzun tutuluyor.")
            else:
                lines.append("Aldığı yeşil süresi, aracın gerçek hızına ve mesafesine göre hesaplanıyor -- sabit bir tahmin değil.")
            return lines

        direction_debug = context.get("direction_debug")

        if not direction_debug:
            return ["İlk karar bekleniyor..."]

        active = {d: info for d, info in direction_debug.items() if info.get("active")}

        if not active:
            return ["Şu anda hiçbir yönde bekleyen araç yok -- mevcut yön minimum yeşilde tutuluyor."]

        queues = {d: info.get("queue", 0) for d, info in active.items()}
        biggest_queue_dir = max(queues, key=queues.get)
        chosen_dir = selected if selected in active else None

        lines = []

        if chosen_dir is None:
            return [reason_full[:160]] if reason_full else ["Karar veriliyor..."]

        chosen_label = labels.get(chosen_dir, chosen_dir.upper())
        biggest_label = labels.get(biggest_queue_dir, biggest_queue_dir.upper())

        if chosen_dir == biggest_queue_dir:
            lines.append(
                f"{chosen_label} en uzun kuyruğa sahip ({int(queues[chosen_dir])} araç bekliyor), "
                f"bu yüzden yeşili alıyor."
            )
        elif "cycle-fairness" in reason_full.lower():
            lines.append(
                f"{biggest_label} yönünde daha çok araç bekliyor ({int(queues[biggest_queue_dir])} vs "
                f"{int(queues[chosen_dir])}), ama bu turda zaten sırası gelmişti -- adalet kuralları, "
                f"tek bir yönün baskın olmasına izin vermeden yeşili {chosen_label} yönüne veriyor."
            )
        else:
            chosen_wait = active.get(chosen_dir, {}).get("excess_wait")
            if chosen_wait:
                lines.append(
                    f"{chosen_label} en büyük kuyruğa sahip değil, ama en uzun süredir bekleyen "
                    f"({chosen_wait:.0f}s, rahat kabul edilen sınırın üzerinde) -- açlığı önlemek burada "
                    f"ham kuyruk büyüklüğüne ağır basıyor."
                )
            else:
                lines.append(
                    f"{chosen_label}, {biggest_label} yerine seçildi -- stratejinin maliyet modeli şu an "
                    f"onu servis etmeyi daha verimli buluyor."
                )

        green_time = context.get("green_time")
        min_g = getattr(self.controller, "min_green", None)
        max_g = getattr(self.controller, "max_green", None)

        if green_time is not None and min_g is not None and max_g is not None:
            if green_time <= min_g:
                lines.append(
                    f"Sadece minimum yeşili alıyor ({green_time}s) -- burada daha uzun tutmayı "
                    f"gerektirecek kadar kuyruk yok."
                )
            elif green_time >= max_g:
                lines.append(
                    f"Yeşil, izin verilen üst sınırda ({green_time}s) -- bu yön boşalırken diğer "
                    f"yönlerin aç kalmaması için."
                )
            else:
                lines.append(
                    f"Yeşil süresi {green_time}s olarak ayarlandı -- bu yönün son hızına göre kuyruğun "
                    f"çoğunu boşaltmaya yetecek kadar, fazla uzatmadan."
                )

        return lines

    def get_next_green_direction(self):
        current = self.get_current_green_direction()

        if self.controller_mode == "fixed":
            current_idx = int(getattr(self.controller, "currentGreen", 0))
            return self.directionNumbers.get((current_idx + 1) % 4, "-")

        # Adaptif modda faz gecisleri reaktif oldugundan (karar, faz
        # BITERKEN aninda verilir, onceden hesaplanmaz), "sirada ne var"
        # sorusunun tek dogru cevabi live bir onizlemedir -- decision_logger/
        # latest_decision_context yalnizca kararin ANINDA anlamli, faz
        # devam ederken (henuz yeni karar verilmediginden) bayat kalir.
        # preview_next_direction() bunun icin yazildi: hicbir state'e
        # yazmayan, her frame guvenle cagrilabilen salt-okunur bir tahmin.
        strategy = getattr(self.controller, "strategy", None)
        preview_fn = getattr(strategy, "preview_next_direction", None)

        if callable(preview_fn):
            try:
                predicted = preview_fn(self, self.controller.params)
            except Exception:
                predicted = None

            if predicted and predicted != current:
                return predicted

        context = getattr(self, "latest_decision_context", {})

        next_green = context.get("next_green")
        if next_green and next_green != "-" and next_green != current:
            return next_green

        selected = context.get("selected_direction")
        if selected and selected != "-" and selected != current:
            return selected

        if self.decision_logger.entries:
            selected = self.decision_logger.entries[-1].get("selected_direction")
            if selected and selected != current:
                return selected

        return "pending"

    def begin_phase_tracking(self, direction, planned_green):
        self.active_phase_tracking = {
            "direction": direction,
            "planned_green": planned_green,
            "start_crossed": self.vehicles[direction]["crossed"],
            "start_time": self.simulation_elapsed,
        }

    def record_completed_phase(self, reason=""):
        tracking = self.active_phase_tracking

        if not tracking:
            return

        direction = tracking["direction"]
        crossed_now = self.vehicles[direction]["crossed"]
        vehicles_crossed = max(0, crossed_now - tracking["start_crossed"])
        actual_green = round(self.simulation_elapsed - tracking["start_time"], 1)

        self.recent_phase_history.append({
            "direction": direction,
            "planned_green": tracking["planned_green"],
            "actual_green": actual_green,
            "vehicles_crossed": vehicles_crossed,
            "reason": reason,
            "time": round(self.simulation_elapsed, 1),
            "redirected": "cycle-fairness" in reason.lower(),
        })

        # Terminal-log paneli 200'e kadar gecmisi scroll edilebilir tutuyor
        # (eski 15'lik "chip" limiti, artik sabit genislikte kutucuklar
        # olmadigindan gerekmiyor).
        if len(self.recent_phase_history) > 200:
            self.recent_phase_history = self.recent_phase_history[-200:]

        self.active_phase_tracking = None

    def update_cycle_compass_state(self):
        current_direction = self.get_current_green_direction()

        if current_direction == "-" or self.get_signal_phase_name() != "GREEN":
            return

        real_served = None
        if self.controller_mode == "adaptive" and hasattr(self, "optimal_cycle_state"):
            real_served = self.optimal_cycle_state.get("served_directions")

        if real_served is not None:
            real_served = set(real_served)

            # 2 saniyelik "tur tamamlandi" penceresi: bu pencere suresince
            # GORSEL sabit kalir (o turda servis edilen -- genelde tum 4
            # yon -- yanik gosterilmeye devam eder), stratejinin kendi ic
            # durumu (real_served) bu sirada zaten yeni turu saymaya
            # baslamis olsa bile. Pencere, o fazin GERCEKTE ne kadar surdugunden
            # BAGIMSIZDIR -- amac fazin bitmesini beklemeden gorseli
            # sifirlamak.
            if self.cycle_completed_pending_reset:
                if self.simulation_elapsed >= self.cycle_completed_flash_until:
                    self.cycle_completed_pending_reset = False
                    # Gorseli sifirlarken, strateji tarafinda o an ZATEN
                    # yeni turun ilk secimi olarak isaretlenmis olani
                    # (carryover) hemen yansit -- boylece "sonraki faz, yeni
                    # cemberin ilk yonu olarak isaretlenmeye devam etsin"
                    # davranisi saglanir.
                    self.cycle_served_directions = set(self._cycle_carryover)
                    self._cycle_prev_real_served = set(real_served)
                return

            if len(real_served) < len(self._cycle_prev_real_served):
                # Strateji kendi ic cycle'ini sifirladi -- yani ONCEKI
                # okumada elimizdeki servis-edilenler seti (cycle_served_directions,
                # genelde tum 4 yon) bir TAM TUR temsil ediyordu. Gorseli
                # HEMEN degistirmiyoruz; 2 saniyelik "tum yollar yandi"
                # penceresini baslatiyoruz. real_served bu noktada zaten
                # yeni turun ilk secimini icerebilir -- flash bitince
                # gorsele tasimak icin sakliyoruz (carryover).
                self.completed_cycle_count += 1
                self.cycle_completed_flash_until = self.simulation_elapsed + 2.0
                self.cycle_completed_pending_reset = True
                self._cycle_carryover = set(real_served)
                self._cycle_prev_real_served = set(real_served)
                return

            newly_added = real_served - self._cycle_prev_real_served
            if newly_added:
                self.cycle_served_directions |= newly_added

            self._cycle_prev_real_served = set(real_served)
            return

        # Fallback: gercek cycle-fairness durumu yoksa (ör. bu garantiye
        # sahip olmayan bir strateji), eski bagimsiz tahmine donulur.
        if self.cycle_completed_pending_reset:
            if self.simulation_elapsed >= self.cycle_completed_flash_until:
                self.cycle_served_directions.clear()
                self.previous_green_direction_for_cycle = current_direction
                self.cycle_completed_pending_reset = False
            return

        if current_direction == self.previous_green_direction_for_cycle:
            return

        self.cycle_served_directions.add(current_direction)
        self.previous_green_direction_for_cycle = current_direction

        if len(self.cycle_served_directions) >= 4:
            self.completed_cycle_count += 1
            self.cycle_completed_flash_until = self.simulation_elapsed + 2.0
            self.cycle_completed_pending_reset = True

    def get_signal_phase_name(self):
        if getattr(self.controller, "currentYellow", 0) == 1:
            return "YELLOW"
        return "GREEN"

    def get_current_signal_remaining(self):
        current = getattr(self.controller, "currentGreen", 0)
        signal = self.controller.signals[current]

        if getattr(self.controller, "currentYellow", 0) == 1:
            return getattr(signal, "yellow", 0)

        return getattr(signal, "green", 0)

    def log_adaptive_decision(
        self,
        phase,
        selected_direction,
        direction_counts,
        calculated_green_time,
        reason,
        direction_debug=None,
        score_semantics=None,
        emergency_priority=False,
    ):
        self.decision_logger.add({
            "time": self.get_current_simulation_time(),
            "phase": phase,
            "selected_direction": selected_direction,
            "direction_counts": dict(direction_counts),
            "calculated_green_time": calculated_green_time,
            "reason": reason,
        })

        # `latest_decision_context` onceden hic guncellenmiyordu (yalnizca
        # __init__'te bir kerelik placeholder set ediliyordu) -- panel bu
        # yuzden emergency box'taki "mode" kontrolu gibi bazi gostergelerde
        # hep bos/varsayilan degeri okuyordu. Artik her karar/olayda
        # guncelleniyor; direction_debug/score_semantics yalnizca gercekten
        # verilmisse (bir strateji karari ise) degistiriliyor, mid-phase
        # olaylarda (emergency_hold/preemption gibi decision_meta'si olmayan
        # cagrilarda) onceki karardan kalan degerler korunuyor.
        if phase in ("emergency_hold", "emergency_preemption"):
            mode = "emergency_hold_priority"
        elif emergency_priority:
            mode = "emergency_priority"
        else:
            mode = "adaptive_decision"

        self.latest_decision_context["selected_direction"] = selected_direction
        self.latest_decision_context["next_green"] = selected_direction
        self.latest_decision_context["reason_full"] = reason
        self.latest_decision_context["mode"] = mode
        self.latest_decision_context["green_time"] = calculated_green_time

        if direction_debug is not None:
            self.latest_decision_context["direction_debug"] = direction_debug
        if score_semantics is not None:
            self.latest_decision_context["score_semantics"] = score_semantics

        # "What the strategy is thinking" log'u -- SADECE gercek faz
        # secimlerinde (phase_change/initial_selection) yeni bir kayit
        # eklenir; mid-phase olaylar (emergency_hold/preemption,
        # continuous_green_extension) burada YENI bir "dusunce" degil,
        # zaten var olan kararin devami oldugundan log'a eklenmez.
        if phase in ("phase_change", "initial_selection"):
            self.decision_narrative_log.append({
                "time": round(self.simulation_elapsed, 1),
                "direction": selected_direction,
                "lines": self.build_decision_narrative(),
            })

            if len(self.decision_narrative_log) > 200:
                self.decision_narrative_log = self.decision_narrative_log[-200:]

    def update_queue_metrics(self):
        if self.simulation_elapsed < self.warmup_time:
            return

        total_queue = 0

        for direction in ["right", "down", "left", "up"]:
            queued = 0

            for lane in self.ACTIVE_LANES:
                for vehicle in self.vehicles[direction][lane]:
                    if vehicle.crossed == 0:
                        queued += 1

            self.queue_samples[direction].append(queued)
            self.queue_peak[direction] = max(
                self.queue_peak[direction],
                queued,
            )
            total_queue += queued

        self.queue_samples["total"].append(total_queue)
        self.queue_peak["total"] = max(
            self.queue_peak["total"],
            total_queue,
        )

    def choose_direction_by_density(self):
        density = self.get_current_direction_density()
        directions = ["right", "down", "left", "up"]

        weights = [
            max(0.0, float(density.get(direction, 0)))
            for direction in directions
        ]

        if sum(weights) <= 0:
            weights = [25, 25, 25, 25]

        chosen = random.choices(directions, weights=weights, k=1)[0]
        return self.directionToNumber[chosen]

    def controller_supports_cycle_fairness(self):
        if self.controller_mode != "adaptive":
            return False

        if not self.controller_version:
            return False

        if not bool(self.controller_version.get("supports_cycle_fairness", False)):
            return False

        return bool(
            self.controller_version.get("params", {}).get(
                "cycle_fairness_enabled", True
            )
        )

    def choose_vehicle_type_by_direction(self, direction):
        distribution = self.config["road_vehicle_distribution"][direction]
        vehicle_order = ["car", "bus", "truck", "bike"]

        weights = [
            max(0.0, float(distribution.get(vehicle_type, 0)))
            if self.allowedVehicleTypes.get(vehicle_type, False)
            else 0.0
            for vehicle_type in vehicle_order
        ]

        if sum(weights) <= 0:
            enabled_types = [
                vehicle_type
                for vehicle_type in vehicle_order
                if self.allowedVehicleTypes.get(vehicle_type, False)
            ]

            return random.choice(enabled_types) if enabled_types else "car"

        return random.choices(vehicle_order, weights=weights, k=1)[0]

    def count_active_emergency_vehicles(self):
        count = 0

        for direction in ["right", "down", "left", "up"]:
            for lane in self.ACTIVE_LANES:
                for vehicle in self.vehicles[direction][lane]:
                    if getattr(vehicle, "isEmergency", False) and vehicle.crossed == 0:
                        count += 1

        return count

    def controller_supports_emergency_priority(self):
        if self.controller_mode != "adaptive":
            return False

        if not self.controller_version:
            return False

        return bool(
            self.controller_version.get("params", {}).get(
                "emergency_priority_enabled", True
            )
        )

    def should_spawn_emergency_vehicle(self):
        emergency = self.emergency_config

        if not emergency.get("enabled", False):
            return False

        max_active = int(emergency.get("max_active_emergency", 1))
        if self.count_active_emergency_vehicles() >= max_active:
            return False

        min_gap = float(emergency.get("min_spawn_gap", 20))
        if self.simulation_elapsed - self.last_emergency_spawn_time < min_gap:
            return False

        probability = float(emergency.get("spawn_probability", 0.03))
        return random.random() < probability

    def choose_emergency_vehicle_type(self):
        emergency = self.emergency_config
        vehicle_types = emergency.get("vehicle_types", {})

        enabled_types = [
            vehicle_type
            for vehicle_type in self.emergency_vehicle_types
            if vehicle_types.get(vehicle_type, False)
        ]

        if not enabled_types:
            return None

        return random.choice(enabled_types)

    def choose_turn_intent(self, lane_number):
        lane_policy = self.config["lane_turn_policy"].get(
            str(lane_number),
            ["straight"],
        )

        if lane_number == 1:
            if lane_policy == ["left"]:
                return "left"
            if lane_policy == ["straight"]:
                return "straight"

            return (
                "left"
                if random.random() < float(self.config["left_turn_probability"])
                else "straight"
            )

        if lane_number == 2:
            if lane_policy == ["right"]:
                return "right"
            if lane_policy == ["straight"]:
                return "straight"

            return (
                "right"
                if random.random() < float(self.config["right_turn_probability"])
                else "straight"
            )

        return "straight"

    def collect_results(self, interrupted=False):

        def percentile(values, p):
            if not values:
                return 0.0

            values = sorted(values)

            k = (len(values) - 1) * (p / 100)

            f = int(k)
            c = min(f + 1, len(values) - 1)

            if f == c:
                return values[f]

            return values[f] + (values[c] - values[f]) * (k - f)

        total_wait_values = []
        per_direction = {}

        for direction in ["right", "down", "left", "up"]:
            waits = self.vehicleMetrics[direction]
            total_wait_values.extend(waits)

            direction_summary = summarize_direction(
                waits,
                self.queue_samples[direction],
                self.queue_peak[direction],
            )

            direction_summary["wait_p90"] = round(percentile(waits, 90), 3)
            direction_summary["wait_p95"] = round(percentile(waits, 95), 3)
            direction_summary["wait_p99"] = round(percentile(waits, 99), 3)

            per_direction[direction] = direction_summary

        total_queue_samples = self.queue_samples["total"]

        overall_avg = (
            sum(total_wait_values) / len(total_wait_values)
            if total_wait_values
            else 0.0
        )

        overall_max = max(total_wait_values) if total_wait_values else 0.0

        overall_p50 = percentile(total_wait_values, 50)
        overall_p90 = percentile(total_wait_values, 90)
        overall_p95 = percentile(total_wait_values, 95)
        overall_p99 = percentile(total_wait_values, 99)
        emergency_waits = self.emergencyVehicleMetrics["wait_times"]
        normal_waits = self.normalVehicleMetrics["wait_times"]

        emergency_avg_wait = (
            sum(emergency_waits) / len(emergency_waits)
            if emergency_waits
            else 0.0
        )

        emergency_max_wait = (
            max(emergency_waits)
            if emergency_waits
            else 0.0
        )

        normal_avg_wait = (
            sum(normal_waits) / len(normal_waits)
            if normal_waits
            else 0.0
        )

        normal_p95_wait = percentile(normal_waits, 95)

        priority_metrics = self.emergency_priority_metrics

        # Measured vehicles that never reached the stop line. Their waits are
        # not part of overall_avg_wait, so a controller that leaves many
        # vehicles behind looks better than it is unless this is read with it.
        uncrossed = [
            vehicle
            for direction in ["right", "down", "left", "up"]
            for lane in self.ACTIVE_LANES
            for vehicle in self.vehicles[direction][lane]
            if vehicle.crossed == 0 and vehicle.spawnTime >= self.warmup_time
        ]
        uncrossed_waits = [vehicle.waitTime for vehicle in uncrossed]

        metrics = {
            "overall_avg_wait": round(overall_avg, 3),
            "overall_avg_delay": (
                round(sum(self.vehicleDelays) / len(self.vehicleDelays), 3)
                if self.vehicleDelays
                else 0.0
            ),
            "overall_delay_p95": round(percentile(self.vehicleDelays, 95), 3),
            "vehicles_measured": len(total_wait_values) + len(uncrossed),
            "vehicles_uncrossed": len(uncrossed),
            "uncrossed_avg_wait": (
                round(sum(uncrossed_waits) / len(uncrossed_waits), 3)
                if uncrossed_waits
                else 0.0
            ),
            "overall_median_wait": round(overall_p50, 3),
            "overall_max_wait": round(overall_max, 3),
            "overall_wait_p50": round(overall_p50, 3),
            "overall_wait_p90": round(overall_p90, 3),
            "overall_wait_p95": round(overall_p95, 3),
            "overall_wait_p99": round(overall_p99, 3),
            "queue_length_average": (
                round(sum(total_queue_samples) / len(total_queue_samples), 3)
                if total_queue_samples
                else 0.0
            ),
            "queue_length_peak": int(self.queue_peak["total"]),
            "total_crossed": len(total_wait_values),
            "emergency_spawned": int(self.emergencyVehicleMetrics["spawned"]),
            "emergency_crossed": int(self.emergencyVehicleMetrics["crossed"]),
            "emergency_avg_wait": round(emergency_avg_wait, 3),
            "emergency_max_wait": round(emergency_max_wait, 3),
            "emergency_wait_p95": round(percentile(emergency_waits, 95), 3),
            "emergency_wait_p99": round(percentile(emergency_waits, 99), 3),
            "normal_vehicle_crossed": int(self.normalVehicleMetrics["crossed"]),
            "normal_vehicle_avg_wait": round(normal_avg_wait, 3),
            "normal_vehicle_p95_wait": round(normal_p95_wait, 3),

            "emergency_hold_count": int(
                self.emergencyVehicleMetrics.get("hold_count", 0)
            ),

            "emergency_total_hold_time": round(
                self.emergencyVehicleMetrics.get("total_hold_time", 0.0),
                3,
            ),

            "emergency_hold_success_count": int(
                self.emergencyVehicleMetrics.get("hold_success_count", 0)
            ),

            "emergency_hold_max_time": round(
                self.emergencyVehicleMetrics.get("hold_max_time", 0.0),
                3,
            ),

            "active_emergency_vehicles": int(self.count_active_emergency_vehicles()),
            "priority_activation_count": int(
                priority_metrics.get("priority_activation_count", 0)
            ),
            "avg_discharge_rate": (
                round(
                    sum(self.v8_metrics["avg_discharge_rate_samples"])
                    / len(self.v8_metrics["avg_discharge_rate_samples"]),
                    3,
                )
                if self.v8_metrics["avg_discharge_rate_samples"]
                else 0.0
            ),
            "avg_phase_roi": (
                round(
                    sum(self.v8_metrics["avg_roi_samples"])
                    / len(self.v8_metrics["avg_roi_samples"]),
                    3,
                )
                if self.v8_metrics["avg_roi_samples"]
                else 0.0
            ),
            "phase_extension_count": int(self.v8_metrics["phase_extensions"]),
            "early_cutoff_count": int(self.v8_metrics["early_cutoffs"]),
            "wasted_green_ratio": (
                round(
                    self.v8_metrics["wasted_green_time"]
                    / max(
                        1.0,
                        self.v8_metrics["effective_green_time"]
                        + self.v8_metrics["wasted_green_time"],
                    ),
                    3,
                )
            ),
        }

        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "test_identity": {
                "test_name": self.test_name,
                "scenario_name": self.scenario["scenario_name"],
                "seed": self.random_seed,
            },
            "experiment_identity": {
                "scenario_id": self.scenario["scenario_id"],
                "controller_mode": self.controller_mode,
                "controller_version_id": (
                    self.controller_version["version_id"]
                    if self.controller_version
                    else "fixed_baseline"
                ),
                "state_provider_id": self.state_provider_id,
            },
            "interrupted": interrupted,
            "metrics": metrics,
            "per_direction": per_direction,
            "decision_log": (
                self.decision_logger.entries
                if self.controller_mode == "adaptive"
                else []
            ),
            "config_snapshot": {
                "scenario": self.scenario,
                "controller_version": self.controller_version,
            },
            "phase_performance_history": self.phase_performance_history,
        }

    def generateVehicles(self):
        while self.simulationRunning:
            self.wait_if_paused()

            lane_number = random.choice(self.ACTIVE_LANES)
            direction_number = self.choose_direction_by_density()
            direction = self.directionNumbers[direction_number]

            is_emergency = False
            emergency_type = None

            if self.should_spawn_emergency_vehicle():
                emergency_type = self.choose_emergency_vehicle_type()

                if emergency_type:
                    vehicle_type_name = emergency_type
                    is_emergency = True
                    self.last_emergency_spawn_time = self.simulation_elapsed
                    self.emergency_spawned_count += 1
                    self.emergencyVehicleMetrics["spawned"] += 1
                else:
                    vehicle_type_name = self.choose_vehicle_type_by_direction(direction)
            else:
                vehicle_type_name = self.choose_vehicle_type_by_direction(direction)

            turn_intent = self.choose_turn_intent(lane_number)

            Vehicle(
                self,
                lane_number,
                vehicle_type_name,
                direction_number,
                direction,
                turn_intent,
                self.controller,
                is_emergency=is_emergency,
                emergency_type=emergency_type,
            )

            self.scaled_sleep(self.get_current_spawn_interval())

    def draw_button(self, screen, rect, text, color, font, enabled=True):
        draw_color = color if enabled else (110, 110, 110)

        pygame.draw.rect(screen, draw_color, rect, border_radius=8)
        pygame.draw.rect(
            screen,
            (30, 30, 30),
            rect,
            width=2,
            border_radius=8,
        )

        text_color = (255, 255, 255) if enabled else (210, 210, 210)
        text_surf = font.render(text, True, text_color)
        text_rect = text_surf.get_rect(center=rect.center)

        screen.blit(text_surf, text_rect)

    def draw_detection_area_overlays(self, screen):
        if not self.state_provider_id.startswith("yolo"):
            return

        if not hasattr(self.state_provider, "get_rich_state"):
            return

        rich_state = self.state_provider.get_rich_state()
        label_font = pygame.font.Font(None, 18)

        previous_clip = screen.get_clip()
        screen.set_clip(pygame.Rect(0, 0, 900, 900))

        for direction, info in rich_state.items():
            roi = info["roi"]
            color = tuple(info.get("color", (255, 255, 255)))

            rect = pygame.Rect(
                roi["x_min"],
                roi["y_min"],
                roi["x_max"] - roi["x_min"],
                roi["y_max"] - roi["y_min"],
            )

            pygame.draw.rect(screen, color, rect, width=3)

            queue_level_tr = {"unknown": "bilinmiyor"}.get(info["queue_level"], info["queue_level"])
            label = f"{self.SIGNAL_LABELS.get(direction, direction.upper())} {queue_level_tr}"
            label_surf = label_font.render(label, True, color)

            bg_rect = label_surf.get_rect(topleft=(rect.x + 4, rect.y + 4))
            pygame.draw.rect(screen, (0, 0, 0), bg_rect.inflate(6, 4))
            screen.blit(label_surf, (rect.x + 7, rect.y + 6))

        screen.set_clip(previous_clip)

    def draw_vehicles_clipped(self, screen, move_vehicles=True):
        road_area = pygame.Rect(0, 0, 900, 900)
        previous_clip = screen.get_clip()

        screen.set_clip(road_area)

        for vehicle in list(self.simulation):
            if hasattr(vehicle, "image"):
                screen.blit(vehicle.image, [vehicle.x, vehicle.y])

                if hasattr(vehicle, "draw_wait_time"):
                    vehicle.draw_wait_time(screen)

                if move_vehicles:
                    vehicle.move()

        screen.set_clip(previous_clip)

    def get_rich_state_for_panel(self):
        if hasattr(self.state_provider, "get_rich_state"):
            return self.state_provider.get_rich_state()

        raw_state = self.state_provider.get_state()

        return {
            direction: {
                "queue_count": value,
                "visible_count": None,
                "score": None,
                "queue_level": None,
                "color": (230, 230, 230),
            }
            for direction, value in raw_state.items()
        }

    def wrap_text(self, text, max_chars):
        words = str(text).split()
        lines = []
        current = ""

        for word in words:
            candidate = f"{current} {word}".strip()

            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word

        if current:
            lines.append(current)

        return lines

    def draw_professional_side_panel(
        self,
        screen,
        panel_x,
        panel_y,
        panel_w,
        panel_h,
        title_font,
        font,
        small_font,
    ):
        # ============================================================
        # Kontrol paneli -- projedeki adaptif karar mekanizmalarinin
        # ("neden bu yon, neden bu sure, cycle-fairness gercekten calisiyor
        # mu, ogrenilen parametreler ne durumda") CANLI ve GERCEK veriyle
        # gorsellestirildigi tek yer. Tum degerler ya dogrudan strateji
        # kararindan (decision_meta/direction_debug, bkz. controllers/
        # strategies/*.py) ya da motorun kendi olcumlerinden geliyor --
        # kozmetik/hardcode bir sayi yok.
        # ============================================================

        DIRECTIONS = ["right", "down", "left", "up"]
        DIRECTION_LABELS = self.SIGNAL_LABELS
        PHASE_LABELS_TR = {"GREEN": "YEŞİL", "YELLOW": "SARI", "RED": "KIRMIZI"}

        PALETTE = {
            "bg": (19, 20, 24),
            "card": (27, 28, 33),
            "card_alt": (32, 34, 40),
            "border": (52, 54, 62),
            "text": (232, 233, 238),
            "text_dim": (152, 154, 164),
            "text_faint": (98, 100, 110),
            "green": (58, 217, 152),
            "amber": (255, 180, 74),
            "red": (255, 92, 92),
            "blue": (94, 168, 255),
            "purple": (176, 137, 255),
            "right": (255, 145, 96),
            "down": (94, 190, 255),
            "left": (180, 140, 255),
            "up": (255, 210, 92),
        }


        pygame.draw.rect(screen, PALETTE["bg"], (panel_x, panel_y, panel_w, panel_h))
        pygame.draw.rect(screen, PALETTE["border"], (panel_x, panel_y, panel_w, panel_h), 2)

        # ---- primitives ----------------------------------------------

        def draw_text(text, tx, ty, color=PALETTE["text"], used_font=None):
            used_font = used_font or font
            surf = used_font.render(str(text), True, color)
            screen.blit(surf, (tx, ty))
            return surf.get_width()

        def draw_right_text(text, right_x, ty, color=PALETTE["text"], used_font=None):
            used_font = used_font or font
            surf = used_font.render(str(text), True, color)
            screen.blit(surf, (right_x - surf.get_width(), ty))

        def section_title(text, tx, ty, color=PALETTE["text"]):
            draw_text(text.upper(), tx, ty, color, small_font)

        def draw_wrapped_text(text, tx, ty, max_width, color, used_font=None, line_height=14, max_lines=4):
            used_font = used_font or small_font
            words = str(text).split(" ")
            lines = []
            current = ""

            for word in words:
                trial = f"{current} {word}".strip()

                if used_font.size(trial)[0] <= max_width or not current:
                    current = trial
                else:
                    lines.append(current)
                    current = word

                if len(lines) >= max_lines:
                    break

            if current and len(lines) < max_lines:
                lines.append(current)

            for i, line in enumerate(lines[:max_lines]):
                draw_text(line, tx, ty + i * line_height, color, used_font)

            return ty + len(lines[:max_lines]) * line_height

        def card(cx, cy, cw, ch, border_color=None):
            pygame.draw.rect(screen, PALETTE["card"], (cx, cy, cw, ch), border_radius=10)
            pygame.draw.rect(
                screen, border_color or PALETTE["border"], (cx, cy, cw, ch), 1, border_radius=10
            )

        def status_pill(text, active, px, py, color_on=None):
            color = (color_on or PALETTE["green"]) if active else PALETTE["text_faint"]
            label = "AKTİF" if active else "KAPALI"
            surf = small_font.render(f"{text}: {label}" if text else label, True, color)
            pad_x, pad_y = 8, 3
            w, h = surf.get_width() + pad_x * 2, surf.get_height() + pad_y * 2
            pygame.draw.rect(
                screen,
                (color[0] // 5, color[1] // 5, color[2] // 5),
                (px, py, w, h),
                border_radius=h // 2,
            )
            pygame.draw.rect(screen, color, (px, py, w, h), 1, border_radius=h // 2)
            screen.blit(surf, (px + pad_x, py + pad_y))
            return w

        def hbar_row(label, value, max_value, bx, by, bw, color, value_text=None, sub_label=None):
            draw_text(label, bx, by, PALETTE["text_dim"], small_font)
            bar_x = bx + 26
            bar_w = bw - 26 - 46
            bar_h = 10
            bar_y = by + 2

            pygame.draw.rect(screen, PALETTE["card_alt"], (bar_x, bar_y, bar_w, bar_h), border_radius=5)

            ratio = 0.0 if max_value <= 0 else max(0.0, min(1.0, value / max_value))
            fill_w = max(3, int(bar_w * ratio)) if value > 0 else 0

            if fill_w > 0:
                pygame.draw.rect(screen, color, (bar_x, bar_y, fill_w, bar_h), border_radius=5)

            draw_right_text(
                value_text if value_text is not None else f"{value:.0f}",
                bx + bw,
                by,
                PALETTE["text"],
                small_font,
            )

            if sub_label:
                draw_text(sub_label, bar_x, by + 12, PALETTE["text_faint"], small_font)

        def count_queue(direction):
            # Stratejinin GERCEKTEN gordugu kuyruk ile ayni tanim (bkz.
            # state_providers/ground_truth_provider.py) -- sadece fiilen
            # bloke/bekleyen araclar, henuz kavsaga yaklasmamis (serbest
            # ilerleyen) araclar HARIC.
            return sum(
                1
                for lane in self.ACTIVE_LANES
                for vehicle in self.vehicles[direction][lane]
                if vehicle.crossed == 0 and vehicle.waitingDueToSignalQueue
            )

        def count_approaching(direction):
            # Henuz kesisimi gecmemis ama kuyruga da hic yaklasmamis
            # (serbestce ilerleyen) arac sayisi -- "toplam kac arac sistemde
            # var" ile "kac tanesi GERCEKTEN bekliyor" arasindaki farki
            # panelde gorunur kilar.
            return sum(
                1
                for lane in self.ACTIVE_LANES
                for vehicle in self.vehicles[direction][lane]
                if vehicle.crossed == 0 and not vehicle.waitingDueToSignalQueue
            )

        def is_vehicle_on_screen(vehicle):
            # Sim alani sabit 900x900 (bkz. run()'daki SIM_AREA_W). Aracin
            # kutusu bu alanla kesisiyorsa "gorunur" sayilir.
            rect = vehicle.image.get_rect()
            return (
                vehicle.x + rect.width > 0 and vehicle.x < 900
                and vehicle.y + rect.height > 0 and vehicle.y < 900
            )

        def count_visible_approaching(direction):
            # count_approaching()'in bir alt kumesi: henuz bekleme
            # durumuna gecmemis AMA zaten 900x900 gorunur alanin icinde
            # olan (yani birkac saniye icinde kuyruga eklenecek) araclar.
            # Su durumu gorunur kilar: "yaklasan"
            # sayisi buyuk olsa da bunlarin cogu ekranin disinda,
            # kavsaga hala uzaktaysa, karar mekanizmasinin bunu gormemesi
            # (sadece 'bekleyen' sayisina bakmasi) kisa vadede sorun
            # olmayabilir; ama gorunur alanda cok sayida yaklasan arac
            # varsa bu, "birazdan kuyruk patlayacak" sinyalidir.
            return sum(
                1
                for lane in self.ACTIVE_LANES
                for vehicle in self.vehicles[direction][lane]
                if vehicle.crossed == 0
                and not vehicle.waitingDueToSignalQueue
                and is_vehicle_on_screen(vehicle)
            )

        def count_emergency(direction):
            # Sadece GERCEKTEN kuyrukta bloke olmus (waitingDueToSignalQueue)
            # acil durum araclarini say -- serbestce ilerleyen, kavsaga hic
            # yaklasmamis bir acil durum araci icin "ACİL" rozeti gostermek
            # (karar mekanizmasi zaten bu araclari yok sayarken) yaniltici,
            # digerlerinin "anlamsiz aciliyet" gibi algilanmasina yol aciyordu.
            return sum(
                1
                for lane in self.ACTIVE_LANES
                for vehicle in self.vehicles[direction][lane]
                if getattr(vehicle, "isEmergency", False)
                and vehicle.crossed == 0
                and getattr(vehicle, "waitingDueToSignalQueue", False)
            )

        x = panel_x + 16
        content_w = panel_w - 32
        y = panel_y + 12

        # ---- header (compact) ------------------------------------------
        # Mode/Speed/Seed/Scenario etiketleri onceden simulasyon gorunumunun
        # ustune ayrica yaziliyordu -- artik burada, panelin basinda.

        def truncate_to_width(text, max_w, used_font):
            truncated = text
            while used_font.size(truncated)[0] > max_w and len(truncated) > 4:
                truncated = truncated[:-1]
            return truncated

        scenario_name = self.scenario.get("scenario_name", "-")
        draw_text(
            truncate_to_width(scenario_name, content_w - 70, title_font),
            x, y, PALETTE["text"], title_font,
        )
        draw_right_text(
            f"{self.simulation_elapsed:.0f}s / {self.simulation_time:.0f}s",
            x + content_w, y + 2, PALETTE["text_faint"], small_font,
        )
        y += 20

        controller_name = "Sabit Süreli (Baseline)"
        if self.controller_mode == "adaptive" and self.controller_version:
            controller_name = self.controller_version.get("display_name", "-")
        controller_name_short = truncate_to_width(controller_name.split(" (")[0], content_w, small_font)

        draw_text(controller_name_short, x, y, PALETTE["text_dim"], small_font)
        y += 17

        mode_label_tr = "adaptif" if self.controller_mode == "adaptive" else "sabit süreli"
        stat_line = (
            f"mod: {mode_label_tr}   hız: {self.playback_speed}x   "
            f"tohum: {self.random_seed}   sağlayıcı: {self.state_provider_id}"
        )
        draw_text(truncate_to_width(stat_line, content_w, small_font), x, y, PALETTE["text_faint"], small_font)
        y += 20

        # ---- hero: 4 ayri trafik isigi widget'i (bir yon = bir isik) --------
        # Onceden tek bir kavsak glifi + tek yonun bilgisi gosteriliyordu.
        # Artik her yonun KENDI isigi (R/Y/G lamba yigini), kendi fazi ve
        # kendi suresiyle ayri ayri gosteriliyor -- "hangi yonun hangi fazda
        # oldugu" hicbir belirsizlik birakmadan net.

        current_direction = self.get_current_green_direction()
        next_direction = self.get_next_green_direction()
        phase = self.get_signal_phase_name()
        remaining = self.get_current_signal_remaining()

        repeat_count = (
            getattr(self.controller, "same_direction_repeat_count", 0)
            if self.controller_mode == "adaptive"
            else 0
        )

        # Onceden burada (ayri bir "oncelik siralamasi" kartinin altinda)
        # bir de "yol bazinda canli ozet" tablosu vardi -- artik o veri
        # (kuyruk/bekleyen/ort-mak bekleme/gecen/ogrenilen discharge_rate)
        # DOGRUDAN her yonun kendi kutusunun icinde gosteriliyor; ayri
        # tablo ve "oncelik siralamasi" karti kaldirildi (tek
        # bakista hem isik hem ozet).
        runtime_all = getattr(self, "optimal_direction_runtime", {})

        widget_gap = 10
        widget_w = (content_w - 16 - widget_gap * 3) / 4
        widget_h = 162
        legend_h = 14
        hero_h = widget_h + 10 + legend_h + (16 if repeat_count > 0 else 0)
        card(x, y, content_w, hero_h)
        widget_y = y + 8

        for idx, direction in enumerate(DIRECTIONS):
            wx = x + 8 + idx * (widget_w + widget_gap)

            is_current = direction == current_direction
            is_next = (not is_current) and direction == next_direction

            if is_current and phase == "GREEN":
                lit_state, border_color = "green", PALETTE["green"]
            elif is_current and phase == "YELLOW":
                lit_state, border_color = "yellow", PALETTE["amber"]
            else:
                lit_state, border_color = "red", (PALETTE["blue"] if is_next else PALETTE["border"])

            pygame.draw.rect(screen, PALETTE["card_alt"], (wx, widget_y, widget_w, widget_h), border_radius=8)
            pygame.draw.rect(screen, border_color, (wx, widget_y, widget_w, widget_h), 2, border_radius=8)

            center_x = wx + widget_w / 2

            draw_text(
                DIRECTION_LABELS[direction], wx + 8, widget_y + 6,
                PALETTE["text"] if is_current else PALETTE["text_dim"], small_font,
            )

            # rozetler: SIRADA (bir sonraki yesil) ve ACİL (bu yonde
            # bekleyen bir acil durum araci var) -- ikisi ayni anda da
            # olabilir, bu yuzden ust uste iki ayri satirda.
            emergency_count = count_emergency(direction)
            badge_y = widget_y + 4

            if is_next:
                next_label = "SIRADA"
                badge_w = small_font.size(next_label)[0] + 10
                badge_x = wx + widget_w - badge_w - 6
                pygame.draw.rect(screen, PALETTE["blue"], (badge_x, badge_y, badge_w, 16), border_radius=8)
                draw_text(next_label, badge_x + 5, badge_y + 2, (15, 15, 18), small_font)
                badge_y += 18

            if emergency_count > 0:
                em_label = "ACİL"
                badge_w = small_font.size(em_label)[0] + 10
                badge_x = wx + widget_w - badge_w - 6
                pygame.draw.rect(screen, PALETTE["red"], (badge_x, badge_y, badge_w, 16), border_radius=8)
                draw_text(em_label, badge_x + 5, badge_y + 2, (15, 15, 18), small_font)

            light_r = 7
            light_gap = 18
            light_top_y = widget_y + 30
            light_colors = {"red": PALETTE["red"], "yellow": PALETTE["amber"], "green": PALETTE["green"]}

            for i, state in enumerate(["red", "yellow", "green"]):
                lit = state == lit_state
                color = light_colors[state] if lit else (45, 46, 52)
                cy = light_top_y + i * light_gap
                pygame.draw.circle(screen, color, (int(center_x), int(cy)), light_r)
                if lit:
                    pygame.draw.circle(screen, (255, 255, 255), (int(center_x), int(cy)), light_r, 1)

            status_y = widget_y + 86

            if is_current:
                status_text = PHASE_LABELS_TR.get(phase, phase)
                status_color = border_color
                time_text = f"{remaining}s"
            else:
                signal_idx = self.directionToNumber.get(direction)
                red_value = getattr(self.controller.signals[signal_idx], "red", None) if signal_idx is not None else None
                status_text = PHASE_LABELS_TR["RED"]
                status_color = PALETTE["text_faint"]
                time_text = f"{red_value}s" if isinstance(red_value, (int, float)) and red_value <= 10 else "--"

            status_surf = small_font.render(status_text, True, status_color)
            screen.blit(status_surf, status_surf.get_rect(center=(center_x, status_y)))
            time_surf = small_font.render(time_text, True, PALETTE["text_dim"])
            screen.blit(time_surf, time_surf.get_rect(center=(center_x, status_y + 16)))

            # ---- yol bazinda canli ozet (eskiden ayri bir tablodaydi,
            # bkz. yukaridaki yorum) -- ayni tanimlar: count_queue/
            # count_approaching/count_visible_approaching yukarida
            # tanimli, waitTime dogrudan arac nesnelerinden okunuyor.
            waits = [
                float(getattr(v, "waitTime", 0.0))
                for lane in self.ACTIVE_LANES
                for v in self.vehicles[direction][lane]
                if v.crossed == 0
            ]
            avg_wait = sum(waits) / len(waits) if waits else 0.0
            max_wait = max(waits) if waits else 0.0
            waiting = sum(1 for w in waits if w > 0.05)
            queue = count_queue(direction)
            approaching = count_approaching(direction)
            visible_approaching = count_visible_approaching(direction)
            crossed = self.vehicles[direction]["crossed"]
            starvation = self.get_direction_starvation_score(direction)

            # Renk kodlama: sayilar tek bir noreme metin yerine ciddiyete
            # gore renkleniyor -- panele tek bakista "hangi yon dikkat
            # istiyor" sorusuna cevap versin diye.
            if queue >= 10:
                queue_color = PALETTE["red"]
            elif queue >= 5:
                queue_color = PALETTE["amber"]
            elif queue > 0:
                queue_color = PALETTE["text"]
            else:
                queue_color = PALETTE["text_faint"]

            wait_line_color = PALETTE["red"] if (queue > 0 and starvation > 20) else PALETTE["text"]

            stats_y = widget_y + 118
            draw_text(f"K:{queue}  B:{waiting}  Y:{approaching}({visible_approaching})", wx + 8, stats_y, queue_color, small_font)
            draw_text(f"Ort:{avg_wait:.0f}s  Mak:{max_wait:.0f}s", wx + 8, stats_y + 13, wait_line_color, small_font)

            runtime = runtime_all.get(direction)
            learned_text = "Öğr:--"
            learned_color = PALETTE["text_faint"]
            if runtime is not None:
                learned_text = f"Öğr:{runtime.get('discharge_rate', 0.0):.2f}a/s"
                learned_color = PALETTE["purple"]
            crossed_label = f"G:{crossed}  "
            draw_text(crossed_label, wx + 8, stats_y + 26, PALETTE["text_faint"], small_font)
            crossed_label_w = small_font.size(crossed_label)[0]
            draw_text(learned_text, wx + 8 + crossed_label_w, stats_y + 26, learned_color, small_font)

            if queue > 0 and starvation > 20:
                # Onceden bu nokta sag-ust kosede (widget_y+6) ciziliyordu --
                # SIRADA/ACİL rozetleriyle AYNI kose, ayni anda birden fazla
                # yon acliksa (gecerli bir durum, ozel bir sey degil) rozetin
                # tam ustune biniyor, kullaniciya "rozet bozuk" gibi
                # goruntuluyordu. Rozetlerden tamamen ayri bir kosede
                # (sag-alt) gosteriliyor artik.
                pygame.draw.circle(
                    screen, PALETTE["red"], (int(wx + widget_w - 8), int(widget_y + widget_h - 8)), 4
                )

        legend_y = widget_y + widget_h + 6
        legend_text = truncate_to_width(
            "K:Kuyrukta  B:Bekliyor  Y:Yaklaşan(görünür)  Ort/Mak:Bekleme  G:Geçen  Öğr:Öğrenilen boşalma hızı",
            content_w - 24, small_font,
        )
        draw_text(legend_text, x + 12, legend_y, PALETTE["text_faint"], small_font)

        if repeat_count > 0:
            current_label = DIRECTION_LABELS.get(current_direction, current_direction or "-")
            draw_text(
                f"{current_label} üst üste {repeat_count + 1}. kez yeşil aldı",
                x + 12, legend_y + legend_h + 2, PALETTE["amber"], small_font,
            )

        y += hero_h + 12

        # ---- what the strategy is thinking: scrollable terminal log --------
        # Onceki surumde burada stratejinin ham `reason` string'i (queue=5,
        # discharge_rate=0.44 gibi degisken dump'i) TEK bir statik kutuda
        # gosteriliyordu. Artik Priority Ranking'in HEMEN altinda, Recent
        # Green Phases ile ayni terminal-log gorunumunde, HER gercek karar
        # icin ayri bir kayit biriktiren, fare tekerlegiyle gecmise
        # kaydirilabilen bir log (bkz. log_adaptive_decision'daki
        # decision_narrative_log.append cagrisi).

        think_h = 150
        card(x, y, content_w, think_h)
        section_title("strateji ne düşünüyor", x + 12, y + 8, PALETTE["text_dim"])
        draw_right_text("geçmiş için kaydır", x + content_w - 12, y + 8, PALETTE["text_faint"], small_font)

        think_x = x + 10
        think_y = y + 26
        think_w = content_w - 20
        think_inner_h = think_h - 34

        pygame.draw.rect(screen, (11, 12, 14), (think_x, think_y, think_w, think_inner_h), border_radius=6)
        pygame.draw.rect(screen, PALETTE["border"], (think_x, think_y, think_w, think_inner_h), 1, border_radius=6)

        self._narrative_log_rect = pygame.Rect(think_x, think_y, think_w, think_inner_h)

        if self.controller_mode != "adaptive":
            draw_text(
                "$ sabit süreli döngü -- her yön eşit ve değişmeyen bir yeşil süresi alır.",
                think_x + 8, think_y + 6, PALETTE["text_faint"], small_font,
            )
        else:
            entry_line_h = 14
            entry_lines_per_block = 4  # 1 baslik + en fazla 3 gerekce satiri
            entry_block_h = entry_line_h * entry_lines_per_block + 6
            visible_count = max(1, think_inner_h // entry_block_h)

            total = len(self.decision_narrative_log)
            max_offset = max(0, total - visible_count)
            self.narrative_scroll_offset = max(0, min(self.narrative_scroll_offset, max_offset))
            offset = self.narrative_scroll_offset

            end = total - offset
            start = max(0, end - visible_count)
            visible_slice = self.decision_narrative_log[start:end]

            if not visible_slice:
                draw_text("$ ilk karar bekleniyor...", think_x + 8, think_y + 6, PALETTE["text_faint"], small_font)
            else:
                block_y = think_y + 4

                for entry in visible_slice:
                    direction = entry["direction"] or "right"
                    header = f"[{entry.get('time', 0.0):6.1f}s] {DIRECTION_LABELS.get(direction, direction.upper())}"
                    draw_text(header, think_x + 8, block_y, PALETTE.get(direction, PALETTE["text"]), small_font)

                    combined = " ".join(entry.get("lines", []))
                    draw_wrapped_text(
                        combined, think_x + 8, block_y + entry_line_h, think_w - 16,
                        PALETTE["text"], small_font, line_height=entry_line_h, max_lines=3,
                    )

                    block_y += entry_block_h

            if total > visible_count:
                track_h = think_inner_h - 8
                thumb_h = max(14, track_h * visible_count / total)
                thumb_y = think_y + 4
                if max_offset:
                    thumb_y += (track_h - thumb_h) * (1 - offset / max_offset)

                scrollbar_x = think_x + think_w - 6
                pygame.draw.rect(screen, (40, 42, 48), (scrollbar_x, think_y + 4, 3, track_h), border_radius=2)
                pygame.draw.rect(screen, PALETTE["text_faint"], (scrollbar_x, thumb_y, 3, thumb_h), border_radius=2)

        y += think_h + 12

        # ---- cycle fairness + emergency (side by side) ---------------------

        box_h = 128
        box_w = int((content_w - 12) / 2)
        left_box_x = x
        right_box_x = x + box_w + 12

        card(left_box_x, y, box_w, box_h)
        section_title("tur adaleti (cycle fairness)", left_box_x + 12, y + 8, PALETTE["text_dim"])

        cycle_active = self.controller_supports_cycle_fairness()
        status_pill("", cycle_active, left_box_x + box_w - 68, y + 6, PALETTE["green"])

        self.update_cycle_compass_state()

        compass_cx = left_box_x + box_w // 2
        compass_cy = y + 72
        radius = 30

        if self.cycle_completed_pending_reset:
            # Tur tamamlandi -- 2 saniyelik "hover" glow: halka nefes alir
            # gibi buyuyup kuculuyor, gercek fazin ne kadar surdugunden
            # BAGIMSIZ sabit bir sure boyunca.
            elapsed_in_flash = 2.0 - max(0.0, self.cycle_completed_flash_until - self.simulation_elapsed)
            pulse = math.sin(elapsed_in_flash * 6.0)
            glow_r = radius + 10 + int(pulse * 4)
            pygame.draw.circle(screen, PALETTE["amber"], (compass_cx, compass_cy), glow_r, 3)
            pygame.draw.circle(screen, PALETTE["amber"], (compass_cx, compass_cy), glow_r + 6, 1)

        pygame.draw.circle(screen, PALETTE["card_alt"], (compass_cx, compass_cy), radius)
        pygame.draw.circle(screen, PALETTE["border"], (compass_cx, compass_cy), radius, 1)

        compass_points = {
            "up": (compass_cx, compass_cy - radius),
            "right": (compass_cx + radius, compass_cy),
            "down": (compass_cx, compass_cy + radius),
            "left": (compass_cx - radius, compass_cy),
        }

        for direction, point in compass_points.items():
            served = direction in self.cycle_served_directions
            color = PALETTE["green"] if served else (80, 82, 90)
            pygame.draw.line(screen, color, (compass_cx, compass_cy), point, 3)
            pygame.draw.circle(screen, color, point, 4)

        draw_text(f"tamamlanan tur: {self.completed_cycle_count}", left_box_x + 12, y + box_h - 20, PALETTE["text_faint"], small_font)

        card(right_box_x, y, box_w, box_h)
        section_title("acil durum", right_box_x + 12, y + 8, PALETTE["text_dim"])

        emergency_priority_enabled = self.controller_supports_emergency_priority()
        status_pill("", emergency_priority_enabled, right_box_x + box_w - 68, y + 6, PALETTE["green"])

        active_emergency_directions = {
            direction for direction in DIRECTIONS if count_emergency(direction) > 0
        }

        priority_direction = None
        if self.latest_decision_context.get("mode") in ("emergency_priority", "emergency_hold_priority"):
            priority_direction = self.latest_decision_context.get("selected_direction")

        em_cx = right_box_x + box_w // 2
        em_cy = y + 62
        em_arm = 28

        flash_on = int(self.simulation_elapsed * 4) % 2 == 0
        approach_points = {
            "right": (em_cx - em_arm, em_cy),
            "left": (em_cx + em_arm, em_cy),
            "down": (em_cx, em_cy - em_arm),
            "up": (em_cx, em_cy + em_arm),
        }

        pygame.draw.line(screen, (56, 58, 66), (em_cx - em_arm, em_cy), (em_cx + em_arm, em_cy), 10)
        pygame.draw.line(screen, (56, 58, 66), (em_cx, em_cy - em_arm), (em_cx, em_cy + em_arm), 10)
        pygame.draw.circle(screen, PALETTE["card_alt"], (em_cx, em_cy), 10)

        for direction, point in approach_points.items():
            if direction == priority_direction and direction in active_emergency_directions:
                color = PALETTE["red"] if flash_on else (140, 40, 40)
                pygame.draw.line(screen, color, (em_cx, em_cy), point, 4)

            if direction in active_emergency_directions:
                pygame.draw.circle(screen, PALETTE["red"], point, 6)
                pygame.draw.circle(screen, (255, 200, 200), point, 6, 1)

        draw_text(
            f"geçen: {self.emergencyVehicleMetrics['crossed']}",
            right_box_x + 12, y + box_h - 36, PALETTE["text_faint"], small_font,
        )
        priority_count = self.emergency_priority_metrics.get("priority_activation_count", 0)
        draw_text(
            f"öncelik verilen: {priority_count}",
            right_box_x + 12, y + box_h - 20, PALETTE["text_faint"], small_font,
        )

        y += box_h + 12

        # ---- recent green phases: scrollable terminal-style log -------------
        # Onceki surumde yan yana sabit-genislikte kutucuklar vardi. Artik
        # gercek bir log/terminal gorunumu: her satir bir fazi anlatiyor,
        # en yenisi altta, fare tekerlegiyle geriye dogru kaydirilabiliyor
        # (bkz. run()'daki pygame.MOUSEWHEEL islenmesi -- _recent_phases_log_rect
        # ile hangi kutuya isabet ettigi kontrol ediliyor).

        log_h = 168
        card(x, y, content_w, log_h)
        section_title("son yeşil fazlar", x + 12, y + 8, PALETTE["text_dim"])
        draw_right_text("geçmiş için kaydır", x + content_w - 12, y + 8, PALETTE["text_faint"], small_font)

        log_x = x + 10
        log_y = y + 26
        log_w = content_w - 20
        log_inner_h = log_h - 34

        pygame.draw.rect(screen, (11, 12, 14), (log_x, log_y, log_w, log_inner_h), border_radius=6)
        pygame.draw.rect(screen, PALETTE["border"], (log_x, log_y, log_w, log_inner_h), 1, border_radius=6)

        self._recent_phases_log_rect = pygame.Rect(log_x, log_y, log_w, log_inner_h)

        line_h = 15
        visible_count = max(1, (log_inner_h - 8) // line_h)
        total = len(self.recent_phase_history)
        max_offset = max(0, total - visible_count)
        self.recent_phases_scroll_offset = max(0, min(self.recent_phases_scroll_offset, max_offset))
        offset = self.recent_phases_scroll_offset

        end = total - offset
        start = max(0, end - visible_count)
        visible_slice = self.recent_phase_history[start:end]

        if not visible_slice:
            draw_text("$ ilk tamamlanan faz bekleniyor...", log_x + 8, log_y + 6, PALETTE["text_faint"], small_font)
        else:
            line_y = log_y + 6

            for phase_entry in visible_slice:
                direction = phase_entry["direction"]

                prefix = f"[{phase_entry.get('time', 0.0):6.1f}s] "
                draw_text(prefix, log_x + 8, line_y, PALETTE["text_faint"], small_font)
                cursor_x = log_x + 8 + small_font.size(prefix)[0]

                dir_text = f"{DIRECTION_LABELS.get(direction, direction.upper()):<7}"
                draw_text(dir_text, cursor_x, line_y, PALETTE[direction], small_font)
                cursor_x += small_font.size(dir_text)[0]

                detail = f"yeşil {phase_entry['actual_green']:.0f}s  geçen {phase_entry['vehicles_crossed']}"
                if phase_entry.get("redirected"):
                    detail += "  [tur adaleti]"

                draw_text(detail, cursor_x, line_y, PALETTE["text"], small_font)
                line_y += line_h

        if total > visible_count:
            track_h = log_inner_h - 8
            thumb_h = max(14, track_h * visible_count / total)
            thumb_y = log_y + 4
            if max_offset:
                thumb_y += (track_h - thumb_h) * (1 - offset / max_offset)

            scrollbar_x = log_x + log_w - 6
            pygame.draw.rect(screen, (40, 42, 48), (scrollbar_x, log_y + 4, 3, track_h), border_radius=2)
            pygame.draw.rect(screen, PALETTE["text_faint"], (scrollbar_x, thumb_y, 3, thumb_h), border_radius=2)

        y += log_h + 8
    def run(self):
        if self.headless:
            return self.run_headless()

        # Sim alani (kavsak gorseli, arac/isik/durma-donus koordinatlari)
        # her yerde hardcoded 0-900 piksel araliginda calisiyor (bkz.
        # self.x/self.y/self.stopLines/self.defaultStop/self.turnTriggerPoints,
        # hepsi __init__'te sabit) -- pencereyi genisletmek SADECE panele
        # daha fazla yer acar, sim alanini hic etkilemez.
        SIM_AREA_W = 900
        PANEL_W = 640
        WINDOW_W = SIM_AREA_W + PANEL_W

        background = pygame.image.load(str(self.images_dir / "intersection.png"))
        screen = pygame.display.set_mode((WINDOW_W, 900))
        pygame.display.set_caption("TRAFFIC SIMULATION")

        thread1 = threading.Thread(target=self.controller.run, daemon=True)
        thread2 = threading.Thread(target=self.generateVehicles, daemon=True)
        self._worker_threads = [thread1, thread2]

        thread1.start()
        thread2.start()
        pygame.display.set_caption("TRAFFIC SIMULATION")

        redSignalBase = pygame.image.load(
            str(self.images_dir / "signals" / "red.png")
        ).convert_alpha()
        yellowSignalBase = pygame.image.load(
            str(self.images_dir / "signals" / "yellow.png")
        ).convert_alpha()
        greenSignalBase = pygame.image.load(
            str(self.images_dir / "signals" / "green.png")
        ).convert_alpha()

        signal_angles = [0, 90, 180, 270]

        redSignals = {
            angle: pygame.transform.rotate(redSignalBase, angle)
            for angle in signal_angles
        }

        yellowSignals = {
            angle: pygame.transform.rotate(yellowSignalBase, angle)
            for angle in signal_angles
        }

        greenSignals = {
            angle: pygame.transform.rotate(greenSignalBase, angle)
            for angle in signal_angles
        }

        btn_font = pygame.font.Font(None, 22)
        log_font = pygame.font.Font(None, 20)
        log_title_font = pygame.font.Font(None, 24)
        small_font = pygame.font.Font(None, 18)
        signal_label_font = pygame.font.Font(None, 18)

        clock = pygame.time.Clock()

        pause_rect = pygame.Rect(18, 18, 105, 32)
        stop_rect = pygame.Rect(18, 58, 105, 32)
        restart_rect = pygame.Rect(18, 98, 105, 32)

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.stop_simulation()
                    self._join_worker_threads(thread1, thread2)
                    pygame.quit()
                    return {
                        "action": "stopped",
                        "result": self.collect_results(interrupted=True),
                    }

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if pause_rect.collidepoint(event.pos):
                        self.paused = not self.paused
                    elif stop_rect.collidepoint(event.pos):
                        self.request_stop = True
                        self.stop_simulation()
                    elif restart_rect.collidepoint(event.pos):
                        self.request_restart = True
                        self.stop_simulation()

                if event.type == pygame.MOUSEWHEEL:
                    mouse_pos = pygame.mouse.get_pos()
                    log_rect = self._recent_phases_log_rect
                    narrative_rect = self._narrative_log_rect

                    # wheel-up (event.y > 0) -> gecmise dogru kaydir (offset
                    # artar); wheel-down -> en yeniye geri don. Hangi log
                    # kutusu uzerinde oldugu, fareye gore ayri ayri kontrol
                    # edilir -- ikisi de bagimsiz kaydirilabilir.
                    if log_rect and log_rect.collidepoint(mouse_pos):
                        self.recent_phases_scroll_offset = max(
                            0, self.recent_phases_scroll_offset + event.y
                        )
                    elif narrative_rect and narrative_rect.collidepoint(mouse_pos):
                        self.narrative_scroll_offset = max(
                            0, self.narrative_scroll_offset + event.y
                        )

            screen.fill((32, 32, 32))

            screen.set_clip(pygame.Rect(0, 0, 900, 900))
            screen.blit(background, (0, 0))
            screen.set_clip(None)

            pygame.draw.rect(screen, (28, 28, 28), (SIM_AREA_W, 0, PANEL_W, 900))

            for i in range(self.noOfSignals):
                signal_info = self.signalCoods[i]
                signal_pos = signal_info["pos"]
                signal_angle = signal_info["angle"]

                if i == self.controller.currentGreen:
                    if self.controller.currentYellow == 1:
                        signal_surface = yellowSignals[signal_angle]
                    else:
                        signal_surface = greenSignals[signal_angle]
                else:
                    signal_surface = redSignals[signal_angle]

                signal_rect = signal_surface.get_rect(center=signal_pos)
                screen.blit(signal_surface, signal_rect.topleft)

                # Her isigin hangi mantiksal yone ait oldugunu gosteren
                # etiket -- fiziksel konum (ekranda nerede durdugu) ile
                # yon ismi (hangi yone giden trafigin isigi oldugu) arasindaki
                # karisikligi onlemek icin. Panelin ust bolumundeki (hero)
                # etiketlerle AYNI isimler kullanilir.
                direction_name = self.directionNumbers[i]
                label_text = self.SIGNAL_LABELS.get(direction_name, direction_name.upper())
                label_surf = signal_label_font.render(label_text, True, (255, 255, 255))
                label_rect = label_surf.get_rect(
                    midtop=(signal_rect.centerx, signal_rect.bottom + 2)
                )
                pygame.draw.rect(
                    screen, (20, 20, 20),
                    label_rect.inflate(6, 4),
                    border_radius=4,
                )
                screen.blit(label_surf, label_rect)

            # Isik sureleri (saniye) artik simulasyon gorunumunun uzerine
            # yazilmiyor -- bu bilgi kontrol panelindeki SIGNAL/hero
            # bolumunde ("Xs remaining") zaten aciklikla gosteriliyor,
            # kavsak gorseli uzerinde ayrica tekrarlanmasina gerek yok.

            if not self.paused:
                self.prepare_simulation_step()

                self.draw_vehicles_clipped(
                    screen,
                    move_vehicles=True,
                )

                self.draw_detection_area_overlays(screen)

                self.advance_simulation_time()

                self.update_queue_metrics()

                for listener in self.tick_listeners:
                    listener(self)

            else:
                self.draw_vehicles_clipped(screen, move_vehicles=False)
                self.draw_detection_area_overlays(screen)

                overlay = pygame.Surface((900, 900), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 65))
                overlay.fill((0, 0, 0, 0), pause_rect)
                overlay.fill((0, 0, 0, 0), stop_rect)
                overlay.fill((0, 0, 0, 0), restart_rect)
                screen.blit(overlay, (0, 0))

                paused_surf = pygame.font.Font(None, 64).render(
                    "DURAKLATILDI",
                    True,
                    (255, 255, 255),
                )
                screen.blit(
                    paused_surf,
                    paused_surf.get_rect(center=(450, 450)),
                )

            self.draw_button(
                screen,
                pause_rect,
                "Devam Et" if self.paused else "Duraklat",
                (52, 114, 235),
                btn_font,
                True,
            )
            self.draw_button(
                screen,
                stop_rect,
                "Durdur",
                (200, 60, 60),
                btn_font,
                True,
            )
            self.draw_button(
                screen,
                restart_rect,
                "Yeniden Başlat",
                (80, 160, 90),
                btn_font,
                True,
            )

            # Mode/Speed/Time/Seed/Scenario etiketleri artik simulasyon
            # gorunumunun ustune ayri yaziliyordu -- artik panelin kendi
            # basligina tasindi (bkz. draw_professional_side_panel), burasi
            # sadelestirildi.
            self.draw_professional_side_panel(
                screen=screen,
                panel_x=SIM_AREA_W,
                panel_y=0,
                panel_w=PANEL_W,
                panel_h=900,
                title_font=log_title_font,
                font=log_font,
                small_font=small_font,
            )

            pygame.display.update()
            clock.tick(self.fps)

            if self.request_restart:
                self._join_worker_threads(thread1, thread2)
                pygame.quit()
                return {"action": "restart", "result": None}

            if self.request_stop:
                self._join_worker_threads(thread1, thread2)
                pygame.quit()
                return {
                    "action": "stopped",
                    "result": self.collect_results(interrupted=True),
                }

            if self.simulation_elapsed >= self.simulation_time:
                self.stop_simulation()
                break

        self._join_worker_threads(thread1, thread2)
        pygame.quit()

        return {
            "action": "finished",
            "result": self.collect_results(interrupted=False),
        }
    
    def run_headless(self):
        thread1 = threading.Thread(
            target=self.controller.run,
            daemon=True,
        )
        thread2 = threading.Thread(
            target=self.generateVehicles,
            daemon=True,
        )
        self._worker_threads = [thread1, thread2]

        thread1.start()
        thread2.start()

        try:
            while self.simulationRunning:
                self.wait_if_paused()

                self.prepare_simulation_step()

                for vehicle in list(self.simulation):
                    vehicle.move()

                self.advance_simulation_time()

                self.update_queue_metrics()

                for listener in self.tick_listeners:
                    listener(self)

                if self.simulation_elapsed >= self.simulation_time:
                    self.stop_simulation()
                    break

                # Yalnızca çalışma hızını sınırlar.
                # Simülasyon zamanının hesabında kullanılmaz.
                time.sleep(1 / self.fps)

            self._join_worker_threads(thread1, thread2)

            return {
                "action": "finished",
                "result": self.collect_results(interrupted=False),
            }

        except Exception:
            self.stop_simulation()
            self._join_worker_threads(thread1, thread2)
            raise

    def register_v8_phase_metrics(
        self,
        discharge_rate,
        roi,
        green_time,
        released,
    ):
        if not hasattr(self, "v8_metrics"):
            return

        self.v8_metrics["avg_discharge_rate_samples"].append(discharge_rate)
        self.v8_metrics["avg_roi_samples"].append(roi)
        self.v8_metrics["effective_green_time"] += green_time

        if released <= 0:
            self.v8_metrics["wasted_green_time"] += green_time

        self.phase_performance_history.append({
            "time": self.simulation_elapsed,
            "discharge_rate": round(discharge_rate, 3),
            "roi": round(roi, 3),
            "green_time": green_time,
            "released": released,
        })

    def get_current_direction_density(self):
        schedule = self.config.get("dynamic_density_schedule")

        if not schedule:
            return self.config["direction_density"]

        current_time = self.simulation_elapsed

        for phase in schedule:
            start_time = float(phase.get("start_time", 0))
            end_time = float(phase.get("end_time", 0))

            if start_time <= current_time < end_time:
                return phase.get("direction_density", self.config["direction_density"])

        return self.config["direction_density"]

    def get_current_spawn_interval(self):
        schedule = self.config.get("dynamic_spawn_interval_schedule")

        if not schedule:
            return float(self.config["spawn_interval"])

        current_time = self.simulation_elapsed

        for phase in schedule:
            start_time = float(phase.get("start_time", 0))
            end_time = float(phase.get("end_time", 0))

            if start_time <= current_time < end_time:
                return float(phase.get("spawn_interval", self.config["spawn_interval"]))

        return float(self.config["spawn_interval"])