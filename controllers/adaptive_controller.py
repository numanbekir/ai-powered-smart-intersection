from simulation.signal import TrafficSignal

from controllers.strategies.optimal_ground_truth_strategy import OptimalGroundTruthStrategy
from controllers.strategies.rolling_horizon_ground_truth_strategy import (
    RollingHorizonGroundTruthStrategy,
    RollingHorizonGroundTruthV2Strategy,
)

STRATEGY_MAP = {
    "optimal_ground_truth": OptimalGroundTruthStrategy,
    "rolling_horizon_ground_truth": RollingHorizonGroundTruthStrategy,
    "rolling_horizon_ground_truth_v2": RollingHorizonGroundTruthV2Strategy,
}


class AdaptiveSignalController:
    ACTIVE_LANES = [1, 2]

    def __init__(self, engine, state_provider, version_info):
        self.engine = engine
        self.state_provider = state_provider
        self.version_info = version_info
        self.params = version_info["params"]

        strategy_key = version_info["strategy_key"]

        if strategy_key not in STRATEGY_MAP:
            raise ValueError(f"Unknown adaptive strategy: {strategy_key}")

        self.strategy = STRATEGY_MAP[strategy_key]()

        self.min_green = int(self.params["min_green"])
        self.max_green = int(self.params["max_green"])
        self.yellow_time = int(self.params["yellow_time"])

        self.same_direction_repeat_limit = int(
            self.params.get("same_direction_repeat_limit", 0)
        )

        self.continuous_green_extension = int(
            self.params.get("continuous_green_extension", self.min_green)
        )

        self.last_selected_direction = None
        self.same_direction_repeat_count = 0

        self.signals = []
        self.currentGreen = 0
        self.currentYellow = 0

        self.initialize()

    def initialize(self):
        self.signals.clear()

        for _ in range(self.engine.noOfSignals):
            self.signals.append(
                TrafficSignal(
                    red=9999,
                    yellow=self.yellow_time,
                    green=0,
                )
            )

    def should_apply_controller_repeat_guard(self):
        return bool(self.params.get("controller_repeat_guard_enabled", True))

    def get_configured_initial_green_index(self):
        config = getattr(self.engine, "config", None)

        if config is None and hasattr(self.engine, "scenario"):
            config = self.engine.scenario.get("config", {})

        if config is None:
            config = {}

        initial_direction = None

        if "adaptive" in config:
            initial_direction = (
                config["adaptive"].get("initial_green")
                or config["adaptive"].get("initial_green_road")
            )

        if not initial_direction and "fixed" in config:
            initial_direction = (
                config["fixed"].get("initial_green")
                or config["fixed"].get("initial_green_road")
            )

        if not initial_direction:
            initial_direction = (
                config.get("initial_green")
                or config.get("initial_green_road")
            )

        if initial_direction not in self.engine.directionToNumber:
            return None

        return self.engine.directionToNumber[initial_direction]

    def get_active_demand_directions(self, state):
        return [
            direction
            for direction, queue_count in state.items()
            if queue_count > 0 and direction in self.engine.directionToNumber
        ]

    def select_single_demand_direction(self, state):
        active_directions = self.get_active_demand_directions(state)

        if len(active_directions) == 1:
            return self.engine.directionToNumber[active_directions[0]]

        return None

    def has_alternative_demand(self, blocked_direction, state):
        for direction, queue_count in state.items():
            if direction == blocked_direction:
                continue

            if direction not in self.engine.directionToNumber:
                continue

            if queue_count > 0:
                return True

        return False

    def should_extend_current_green_without_yellow(self):
        state = self.state_provider.get_state()

        current_direction = self.engine.directionNumbers[self.currentGreen]
        active_directions = self.get_active_demand_directions(state)

        if len(active_directions) == 0:
            # Kavşak tamamen boş: korunacak hiçbir çapraz trafik yok --
            # sarıya geçip aynı yönü tekrar seçmek (select_and_prepare_phase'in
            # "no active demand" fallback'i zaten aynı yönü döndürür) salt
            # zaman kaybı. Mevcut yönü sarısız uzat.
            return True

        if len(active_directions) != 1:
            return False

        if active_directions[0] != current_direction:
            return False

        current_queue = float(state.get(current_direction, 0))

        if current_queue <= 0:
            return False

        return True

    def extend_current_green_without_yellow(self):
        extension_time = max(1, int(self.continuous_green_extension))

        self.signals[self.currentGreen].green = extension_time

        current_direction = self.engine.directionNumbers[self.currentGreen]
        state = self.state_provider.get_state()

        # Discharge-rate öğrenen stratejiler, faz sonunda gerçek yeşil süresine
        # göre discharge_rate hesaplıyor (update_discharge_after_phase, bkz.
        # controllers/strategies/optimal_ground_truth_strategy.py). Uzatma
        # burada update_strategy_after_completed_green'i atladığından, takip
        # edilen green_time'ı da uzatma kadar artırmazsak nihai hesap eski
        # (kısa) planlı süreyle bölünüp discharge_rate'i yapay şekilde şişirir.
        # NOT: bu deger daha once yanlislikla var olmayan bir attribute'a
        # ("adaptive_phase_tracking") yaziliyordu -- stratejilerin gercekte
        # yazdigi/okudugu attribute "optimal_phase_tracking" (bkz.
        # OptimalGroundTruthStrategy.choose_normal_phase /
        # RollingHorizonGroundTruthStrategy.choose_normal_phase). Bu isim
        # uyusmazligi yuzunden duzeltme hicbir zaman fiilen calismiyordu --
        # uzun sureli continuous-green-extension sonrasi discharge_rate hep
        # yapay sekilde sisiyordu.
        tracking = getattr(self.engine, "optimal_phase_tracking", None)
        if tracking:
            tracking["green_time"] = tracking.get("green_time", 0) + extension_time

        active_directions = self.get_active_demand_directions(state)

        if active_directions:
            demand_note = f"Only {current_direction.upper()} has active demand."
        else:
            demand_note = "No direction has active demand."

        reason = (
            f"Continuous green extension activated. "
            f"{demand_note} "
            f"Yellow phase skipped and green extended by {extension_time} sec."
        )

        self.log_decision(
            phase="continuous_green_extension",
            state=state,
            green_time=extension_time,
            reason=reason,
        )

    def update_values(self):
        for i in range(self.engine.noOfSignals):
            if i == self.currentGreen:
                if self.currentYellow == 0:
                    self.signals[i].green -= 1
                else:
                    self.signals[i].yellow -= 1
            else:
                if self.signals[i].red > 0:
                    self.signals[i].red -= 1

    def prepare_signal_times(self, next_green_index, green_time):
        green_time = int(max(self.min_green, min(green_time, self.max_green)))

        for i in range(self.engine.noOfSignals):
            if i == next_green_index:
                self.signals[i].green = green_time
                self.signals[i].yellow = self.yellow_time
                self.signals[i].red = 0
            else:
                self.signals[i].green = 0
                self.signals[i].yellow = self.yellow_time
                self.signals[i].red = green_time + self.yellow_time

    def choose_phase(self):
        state = self.state_provider.get_state()

        result = self.strategy.choose_next_phase(
            state,
            self.params,
            self.engine,
        )

        # `decision_meta` opsiyoneldir: 3-tuple donen (eski/basit) bir
        # strateji hala calisir, sadece emergency-oncelik metrikleri o
        # strateji icin islenmez.
        if len(result) == 4:
            best_direction, green_time, reason, decision_meta = result
        else:
            best_direction, green_time, reason = result
            decision_meta = {}

        best_index = self.engine.directionToNumber[best_direction]

        return best_index, int(green_time), state, reason, (decision_meta or {})

    def select_best_alternative_phase(self, blocked_direction, state):
        candidates = []

        for direction, queue_count in state.items():
            if direction == blocked_direction:
                continue

            if direction not in self.engine.directionToNumber:
                continue

            if queue_count <= 0:
                continue

            candidates.append((direction, queue_count))

        if not candidates:
            return None

        best_direction, _ = max(candidates, key=lambda item: item[1])

        return self.engine.directionToNumber[best_direction]

    def update_repeat_tracking(self, selected_direction):
        if self.last_selected_direction == selected_direction:
            self.same_direction_repeat_count += 1
        else:
            self.last_selected_direction = selected_direction
            self.same_direction_repeat_count = 0

    def update_strategy_after_completed_green(self):
        if hasattr(self.strategy, "update_discharge_after_phase"):
            try:
                alpha = float(self.params.get("flow_memory_alpha", 0.35))
                self.strategy.update_discharge_after_phase(
                    engine=self.engine,
                    alpha=alpha,
                )
            except TypeError:
                self.strategy.update_discharge_after_phase(self.engine)
            except Exception as e:
                print(f"[WARN] Adaptive strategy post-phase update failed: {e}")

    def hold_current_direction_on_yellow(self):
        current_direction = self.engine.directionNumbers[self.currentGreen]

        for lane in self.ACTIVE_LANES:
            for vehicle in self.engine.vehicles[current_direction][lane]:
                vehicle.stop = self.engine.defaultStop[current_direction]

    def log_decision(self, phase, state, green_time, reason, decision_meta=None):
        decision_meta = decision_meta or {}

        self.engine.log_adaptive_decision(
            phase=phase,
            selected_direction=self.engine.directionNumbers[self.currentGreen],
            direction_counts=state,
            calculated_green_time=green_time,
            reason=reason,
            direction_debug=decision_meta.get("direction_debug"),
            score_semantics=decision_meta.get("score_semantics"),
            emergency_priority=bool(decision_meta.get("emergency_priority", False)),
        )

    def select_and_prepare_phase(self, phase_label):
        next_idx, next_green, state, reason, decision_meta = self.choose_phase()
        next_direction = self.engine.directionNumbers[next_idx]

        if decision_meta.get("emergency_priority"):
            self.engine.emergency_priority_metrics["priority_activation_count"] += 1

        if phase_label == "initial_selection":
            configured_initial_idx = self.get_configured_initial_green_index()

            if configured_initial_idx is not None:
                next_idx = configured_initial_idx
                next_direction = self.engine.directionNumbers[next_idx]
                next_green = self.min_green

                reason += (
                    f" Initial phase selected from scenario config. "
                    f"Configured initial green road={next_direction.upper()}."
                )

        single_demand_idx = self.select_single_demand_direction(state)

        if single_demand_idx is not None:
            next_idx = single_demand_idx
            next_direction = self.engine.directionNumbers[next_idx]

            reason += (
                f" Single demand direction guard activated. "
                f"Only {next_direction.upper()} has active demand."
            )

        if (
            self.should_apply_controller_repeat_guard()
            and phase_label != "initial_selection"
            and self.last_selected_direction == next_direction
            and self.same_direction_repeat_count >= self.same_direction_repeat_limit
            and self.has_alternative_demand(next_direction, state)
        ):
            alternative_idx = self.select_best_alternative_phase(
                blocked_direction=next_direction,
                state=state,
            )

            if alternative_idx is not None:
                blocked_direction = next_direction

                next_idx = alternative_idx
                next_direction = self.engine.directionNumbers[next_idx]

                reason += (
                    f" Same direction repeat guard activated. "
                    f"{blocked_direction.upper()} was blocked after "
                    f"{self.same_direction_repeat_count} repeat(s). "
                    f"{next_direction.upper()} was selected as demand-based alternative."
                )

        next_green = int(max(self.min_green, min(next_green, self.max_green)))

        self.update_repeat_tracking(next_direction)

        # `next_direction`, yukarıdaki override'lardan (initial_selection,
        # single_demand, repeat guard) sonra kesinleşen gerçek yöndür --
        # stratejinin kendi ilk tahmini değil. Cycle-fairness bookkeeping'i
        # bu yüzden burada, tek noktadan işaretleniyor (opt-in hook: strateji
        # tanımlamıyorsa hiç çağrılmaz).
        if hasattr(self.strategy, "mark_cycle_served"):
            self.strategy.mark_cycle_served(self.engine, next_direction)

        self.currentGreen = next_idx
        self.prepare_signal_times(self.currentGreen, next_green)

        self.engine.begin_phase_tracking(next_direction, next_green)

        self.engine.mark_direction_served(
            self.engine.directionNumbers[self.currentGreen]
        )

        self.log_decision(
            phase=phase_label,
            state=state,
            green_time=next_green,
            reason=reason,
            decision_meta=decision_meta,
        )

    def run_green_phase(self):
        # `should_preempt` opt-in bir hook'tur: strateji bunu tanımlamıyorsa
        # bu döngü davranışı hiç değişmez. Tanımlayan bir strateji, devam eden bir
        # yeşili -- bir sonraki doğal faz geçişini beklemeden -- güvenlik
        # kısıtlarına (örn. kendi min_green tabanı doldu mu) bağlı olarak
        # erken kesebilir (gerçek mid-phase preemption).
        planned_green = self.signals[self.currentGreen].green
        can_preempt = hasattr(self.strategy, "should_preempt")
        can_extend = hasattr(self.strategy, "get_green_extension")

        while (
            self.signals[self.currentGreen].green > 0
            and self.engine.simulationRunning
        ):
            self.engine.wait_if_paused()

            if can_extend:
                current_direction = self.engine.directionNumbers[self.currentGreen]
                remaining_green = self.signals[self.currentGreen].green

                try:
                    extension = self.strategy.get_green_extension(
                        engine=self.engine,
                        params=self.params,
                        current_direction=current_direction,
                        remaining_green=remaining_green,
                    )
                except Exception as e:
                    print(f"[WARN] get_green_extension failed: {e}")
                    extension = 0

                if extension:
                    self.signals[self.currentGreen].green += int(extension)
                    planned_green += int(extension)

                    hold_metrics = self.engine.emergencyVehicleMetrics
                    hold_metrics["hold_count"] += 1
                    hold_metrics["total_hold_time"] += int(extension)
                    hold_metrics["hold_max_time"] = max(
                        hold_metrics["hold_max_time"], int(extension)
                    )

                    state = self.state_provider.get_state()
                    self.log_decision(
                        phase="emergency_hold",
                        state=state,
                        green_time=self.signals[self.currentGreen].green,
                        reason=(
                            f"Emergency hold activated. "
                            f"{current_direction.upper()}'s green phase extended by "
                            f"{int(extension)}s to let an emergency vehicle already on "
                            f"this direction clear the intersection."
                        ),
                    )

            if can_preempt:
                current_direction = self.engine.directionNumbers[self.currentGreen]
                elapsed_green = planned_green - self.signals[self.currentGreen].green

                try:
                    should_preempt = self.strategy.should_preempt(
                        engine=self.engine,
                        params=self.params,
                        current_direction=current_direction,
                        elapsed_green_seconds=elapsed_green,
                    )
                except Exception as e:
                    print(f"[WARN] should_preempt failed: {e}")
                    should_preempt = False

                if should_preempt:
                    self.engine.emergency_priority_metrics["priority_activation_count"] += 1

                    state = self.state_provider.get_state()
                    self.log_decision(
                        phase="emergency_preemption",
                        state=state,
                        green_time=elapsed_green,
                        reason=(
                            f"Emergency preemption activated. "
                            f"{current_direction.upper()}'s green phase cut short after "
                            f"{elapsed_green}s (planned {planned_green}s) to yield to an "
                            f"approaching emergency vehicle on another direction."
                        ),
                    )
                    self.signals[self.currentGreen].green = 0
                    break

            self.update_values()
            self.engine.scaled_sleep(1)

    def run_yellow_phase(self):
        self.currentYellow = 1
        self.hold_current_direction_on_yellow()

        while (
            self.signals[self.currentGreen].yellow > 0
            and self.engine.simulationRunning
        ):
            self.engine.wait_if_paused()
            self.update_values()
            self.engine.scaled_sleep(1)

        self.currentYellow = 0

    def run(self):
        self.select_and_prepare_phase("initial_selection")

        while self.engine.simulationRunning:
            self.run_green_phase()

            if not self.engine.simulationRunning:
                break

            if self.should_extend_current_green_without_yellow():
                self.extend_current_green_without_yellow()
                continue

            # Yesil TAM burada bitiyor (sariya gecmeden once) -- panel
            # icin "gercek yesil suresi"ni sariyi dahil etmeden kaydet.
            # reason, bu fazi SECEN kararin (select_and_prepare_phase'in
            # engine.latest_decision_context'e yazdigi) aciklamasi -- terminal
            # log'unda "cycle-fairness redirect" gibi notlari gosterebilmek icin.
            self.engine.record_completed_phase(
                reason=self.engine.latest_decision_context.get("reason_full", "")
            )

            self.update_strategy_after_completed_green()

            self.run_yellow_phase()

            if not self.engine.simulationRunning:
                break

            self.select_and_prepare_phase("phase_change")

    def is_green(self, direction_number):
        return self.currentGreen == direction_number and self.currentYellow == 0