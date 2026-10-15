from simulation.signal import TrafficSignal

from controllers.strategies.demand_strategy import DemandStrategy
from core.i18n import approach_name, t


class AdaptiveSignalController:
    """Runs the signal phases and asks the strategy what to do next.

    The controller owns the timing (green, yellow, one-second steps) and
    never overrides a decision of the strategy. A green that has run out is
    kept, without a yellow, for as long as no other approach has a vehicle.
    """

    def __init__(self, engine, state_provider, version_info):
        self.engine = engine
        self.state_provider = state_provider
        self.version_info = version_info
        self.params = version_info["params"]
        self.strategy = DemandStrategy()

        self.min_green = int(self.params["min_green"])
        self.max_green = int(self.params["max_green"])
        self.yellow_time = int(self.params["yellow_time"])

        self.signals = [
            TrafficSignal(red=9999, yellow=self.yellow_time, green=0)
            for _ in range(engine.noOfSignals)
        ]
        self.currentGreen = 0
        self.currentYellow = 0
        self.keeping_green = False

    def current_direction(self):
        return self.engine.directionNumbers[self.currentGreen]

    def update_values(self):
        for i, signal in enumerate(self.signals):
            if i == self.currentGreen:
                if self.currentYellow == 0:
                    signal.green -= 1
                else:
                    signal.yellow -= 1
            elif signal.red > 0:
                signal.red -= 1

    def prepare_signal_times(self, green_index, green_time):
        for i, signal in enumerate(self.signals):
            signal.yellow = self.yellow_time
            if i == green_index:
                signal.green = green_time
                signal.red = 0
            else:
                signal.green = 0
                signal.red = green_time + self.yellow_time

    def log_decision(self, phase, green_time, reason, meta=None):
        meta = meta or {}
        self.engine.log_adaptive_decision(
            phase=phase,
            selected_direction=self.current_direction(),
            direction_counts=self.state_provider.get_state(),
            calculated_green_time=green_time,
            reason=reason,
            direction_debug=meta.get("direction_debug"),
            score_semantics=meta.get("score_semantics"),
            emergency_priority=bool(meta.get("emergency_priority", False)),
        )

    def start_phase(self, phase_label, previous_direction=None):
        direction, green_time, reason, meta = self.strategy.choose_next_phase(
            self.state_provider.get_observation(),
            self.params,
            self.engine.simulation_elapsed,
            previous_direction,
        )
        green_time = int(max(self.min_green, min(green_time, self.max_green)))

        if meta.get("emergency_priority"):
            self.engine.emergency_priority_metrics["priority_activation_count"] += 1

        self.currentGreen = self.engine.directionToNumber[direction]
        self.keeping_green = False
        self.prepare_signal_times(self.currentGreen, green_time)

        self.strategy.phase_started(direction)
        self.engine.begin_phase_tracking(direction, green_time)
        self.engine.mark_direction_served(direction)
        self.log_decision(phase_label, green_time, reason, meta)

    def run_green_phase(self):
        planned_green = self.signals[self.currentGreen].green
        direction = self.current_direction()

        while self.signals[self.currentGreen].green > 0 and self.engine.simulationRunning:
            self.engine.wait_if_paused()
            observation = self.state_provider.get_observation()
            remaining = self.signals[self.currentGreen].green

            extension = self.strategy.green_extension(
                observation, self.params, direction, remaining
            )
            if extension:
                self.signals[self.currentGreen].green += extension
                planned_green += extension
                self.engine.record_emergency_hold(direction, extension)
                self.log_decision(
                    "emergency_hold",
                    self.signals[self.currentGreen].green,
                    t("sim.reason.hold", approach=approach_name(direction), extension=extension),
                )

            elapsed = planned_green - self.signals[self.currentGreen].green
            if self.strategy.should_preempt(
                observation, self.params, self.engine.simulation_elapsed, direction, elapsed
            ):
                self.engine.emergency_priority_metrics["priority_activation_count"] += 1
                self.log_decision(
                    "emergency_preemption",
                    elapsed,
                    t("sim.reason.preempt", approach=approach_name(direction), elapsed=elapsed),
                )
                self.signals[self.currentGreen].green = 0
                break

            self.update_values()
            self.engine.scaled_sleep(1)

    def another_direction_has_demand(self):
        current = self.current_direction()
        observation = self.state_provider.get_observation()
        return any(
            info["visible_count"] > 0
            for direction, info in observation.items()
            if direction != current
        )

    def keep_green(self):
        """Nobody else is waiting: stay green for one more second instead of
        going through a yellow."""
        self.signals[self.currentGreen].green = 1
        if not self.keeping_green:
            self.keeping_green = True
            self.log_decision(
                "continuous_green_extension",
                1,
                t("sim.reason.keep_green", approach=approach_name(self.current_direction())),
            )

    def run_yellow_phase(self):
        self.currentYellow = 1
        while self.signals[self.currentGreen].yellow > 0 and self.engine.simulationRunning:
            self.engine.wait_if_paused()
            self.update_values()
            self.engine.scaled_sleep(1)
        self.currentYellow = 0

    def run(self):
        self.start_phase("initial_selection")

        while self.engine.simulationRunning:
            self.run_green_phase()
            if not self.engine.simulationRunning:
                break

            if not self.another_direction_has_demand():
                self.keep_green()
                continue

            ended_direction = self.current_direction()
            self.engine.record_completed_phase(
                reason=self.engine.latest_decision_context.get("reason_full", "")
            )
            self.strategy.phase_ended(ended_direction, self.engine.simulation_elapsed)

            self.run_yellow_phase()
            if not self.engine.simulationRunning:
                break

            self.start_phase("phase_change", previous_direction=ended_direction)

    def is_green(self, direction_number):
        return self.currentGreen == direction_number and self.currentYellow == 0
