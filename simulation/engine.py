import copy
import math
import random
import threading
import time

import pygame

from controllers.adaptive_controller import AdaptiveSignalController
from controllers.fixed_time_controller import FixedTimeSignalController
from core.i18n import t
from core.paths import IMAGES_DIR
from simulation.decision_logger import DecisionLogger
from simulation.metrics import summarize_direction
from simulation.panel import SidePanel
from simulation.vehicle import Vehicle
from state_providers.ground_truth_provider import GroundTruthStateProvider
from state_providers.yolo_provider import YoloStateProvider


class SimulationEngine:
    ACTIVE_LANES = [1, 2]

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
        # Fixed-time control observes nothing, so it never loads the detector.
        self.state_provider_id = (
            state_provider_id if controller_mode == "adaptive" else "ground_truth_v1"
        )
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
        self.rotationAngle = 3

        # Vehicle motion (px and simulated seconds). A vehicle accelerates
        # towards its own top speed, keeps `timeHeadway` seconds behind the
        # vehicle ahead and brakes along a curve towards a red light.
        # `timeHeadway` sets the saturation flow of a lane.
        self.acceleration = 25.0
        self.comfortBraking = 40.0
        self.hardBraking = 90.0
        self.timeHeadway = 0.7
        self.startGap = 5.0
        self.turnSpeedFactor = 0.7

        # Area between the four stop lines. A vehicle waits at its line while
        # a vehicle from another approach is still inside.
        self.junctionBox = pygame.Rect(
            self.stopLines["right"],
            self.stopLines["down"],
            self.stopLines["left"] - self.stopLines["right"],
            self.stopLines["up"] - self.stopLines["down"],
        )
        self.junctionVehicles = []
        self.exitRoads = {
            heading: [] for heading in [("x", 1), ("x", -1), ("y", 1), ("y", -1)]
        }

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

        # Completed green phases, for the side panel: real duration and the
        # number of vehicles that crossed.
        self.active_phase_tracking = None
        self.recent_phase_history = []

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
        # `seconds` are simulated seconds. The thread waits until the single
        # authoritative clock (`simulation_elapsed`, advanced by the main loop)
        # reaches its wake-up time, so controller and spawner time never drift
        # from the main loop, whatever the real frame rate is.
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
        # The worker threads exit on their own once `simulationRunning` is false,
        # but the spawner may still be inside an SDL call (image load). Calling
        # pygame.quit() while it is crashed the process, so wait for the threads
        # to finish first.
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


    def mark_direction_served(self, direction):
        self.direction_last_served_at[direction] = self.simulation_elapsed

    def get_current_green_direction(self):
        return self.directionNumbers.get(self.controller.currentGreen, "-")


    def get_next_green_direction(self):
        current = self.get_current_green_direction()

        if self.controller_mode == "fixed":
            current_idx = int(getattr(self.controller, "currentGreen", 0))
            return self.directionNumbers.get((current_idx + 1) % 4, "-")

        # Adaptive phases are decided when the current green ends, not in
        # advance, so "what comes next" can only be a live preview. This is a
        # read-only estimate that is safe to call every frame.
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

    def record_emergency_hold(self, direction, extension):
        """A green was held for an emergency vehicle on `direction`."""
        metrics = self.emergencyVehicleMetrics
        metrics["hold_count"] += 1
        metrics["total_hold_time"] += extension
        metrics["hold_max_time"] = max(metrics["hold_max_time"], extension)

        for lane in (1, 2):
            for vehicle in self.vehicles[direction][lane]:
                if vehicle.isEmergency and vehicle.crossed == 0:
                    vehicle.receivedEmergencyHold = True
                    vehicle.totalEmergencyHoldTime += extension

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
            "emergency": "acil durum" in reason.lower(),
        })

        # The side panel shows up to the last 200 phases.
        if len(self.recent_phase_history) > 200:
            self.recent_phase_history = self.recent_phase_history[-200:]

        self.active_phase_tracking = None


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

        # Updated on every decision and event. direction_debug and
        # score_semantics are only replaced by real strategy decisions;
        # mid-phase events (emergency hold, preemption) keep the previous ones.
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


    def draw_detection_area_overlays(self, screen):
        if not self.state_provider_id.startswith("yolo"):
            return

        if not hasattr(self.state_provider, "detect_for_display"):
            return

        label_font = pygame.font.Font(None, 17)
        emergency_classes = {"ambulance", "police", "firetruck"}

        previous_clip = screen.get_clip()
        screen.set_clip(pygame.Rect(0, 0, 900, 900))

        for name, confidence, (x1, y1, x2, y2) in self.state_provider.detect_for_display():
            color = (235, 60, 60) if name in emergency_classes else (60, 190, 250)
            rect = pygame.Rect(int(x1), int(y1), int(x2 - x1), int(y2 - y1))
            pygame.draw.rect(screen, color, rect, width=2)

            label_surf = label_font.render(f"{name} {confidence:.2f}", True, (20, 20, 20))
            label_rect = label_surf.get_rect()
            label_rect.bottomleft = (rect.x, rect.y) if rect.y > 16 else (rect.x, rect.bottom + label_rect.height)
            pygame.draw.rect(screen, color, label_rect.inflate(6, 2))
            screen.blit(label_surf, label_rect)

        screen.set_clip(previous_clip)

    def draw_vehicles_clipped(self, screen, move_vehicles=True):
        road_area = pygame.Rect(0, 0, 900, 900)
        previous_clip = screen.get_clip()

        screen.set_clip(road_area)

        for vehicle in list(self.simulation):
            if hasattr(vehicle, "image"):
                screen.blit(vehicle.image, [vehicle.x, vehicle.y])

                # With the camera provider the vehicles carry detection
                # boxes instead; the wait time is not something it sees.
                if hasattr(vehicle, "draw_wait_time") and not self.state_provider_id.startswith("yolo"):
                    vehicle.draw_wait_time(screen)

                if move_vehicles:
                    vehicle.move()

        screen.set_clip(previous_clip)


    def run(self):
        if self.headless:
            return self.run_headless()

        # The intersection area is fixed at 900x900 px (all coordinates in
        # __init__ assume it). A wider window only adds room for the panel.
        SIM_AREA_W = 900
        PANEL_W = 640
        WINDOW_W = SIM_AREA_W + PANEL_W

        background = pygame.image.load(str(self.images_dir / "intersection.png"))
        screen = pygame.display.set_mode((WINDOW_W, 900))
        pygame.display.set_caption("AI-Powered Smart Intersection")

        thread1 = threading.Thread(target=self.controller.run, daemon=True)
        thread2 = threading.Thread(target=self.generateVehicles, daemon=True)
        self._worker_threads = [thread1, thread2]

        thread1.start()
        thread2.start()
        pygame.display.set_caption("AI-Powered Smart Intersection")

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

        signal_label_font = pygame.font.Font(None, 18)
        panel = SidePanel(self, (SIM_AREA_W, 0, PANEL_W, 900))

        clock = pygame.time.Clock()

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
                    button = panel.button_at(event.pos)
                    if button == "pause":
                        self.paused = not self.paused
                    elif button == "stop":
                        self.request_stop = True
                        self.stop_simulation()
                    elif button == "restart":
                        self.request_restart = True
                        self.stop_simulation()

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

                # Label every signal with the approach it controls, using the same
                # names as the side panel.
                direction_name = self.directionNumbers[i]
                label_text = t(f"sim.signal.{direction_name}")
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
                screen.blit(overlay, (0, 0))

                paused_surf = pygame.font.Font(None, 64).render(
                    t("sim.paused"),
                    True,
                    (255, 255, 255),
                )
                screen.blit(
                    paused_surf,
                    paused_surf.get_rect(center=(450, 450)),
                )

            panel.draw(screen)

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

                # Only limits the real frame rate.
                # Not used for simulated time.
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