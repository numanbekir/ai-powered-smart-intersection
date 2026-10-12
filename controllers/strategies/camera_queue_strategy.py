import math

from controllers.strategies.base_strategy import BaseAdaptiveStrategy


class CameraQueueStrategy(BaseAdaptiveStrategy):
    """Adaptive control from camera observations only.

    Applies the same decision rule as the optimal ground-truth strategy
    (queue + fairness index, cycle fairness, capped green, emergency
    priority), but every input comes from the YOLO state provider or from
    the controller's own clock. Vehicle positions, speeds and wait times
    are never read from the simulation, so the gap to the ground-truth
    controller is the cost of perceiving the intersection through a camera.
    """

    strategy_key = "camera_queue"
    score_semantics = {"label": "index (queue+λ·excess_red)", "higher_is_better": True}
    DIRECTIONS = ["right", "down", "left", "up"]

    def __init__(self):
        self.served_directions = set()
        self.last_green_end = {direction: 0.0 for direction in self.DIRECTIONS}
        self.hold_direction = None
        self.hold_total = 0.0

    def observation(self, engine):
        return engine.controller.state_provider.get_observation()

    def mark_cycle_served(self, engine, direction):
        if direction is not None:
            self.served_directions.add(direction)

    def update_discharge_after_phase(self, engine, alpha=0.35):
        direction = engine.directionNumbers.get(engine.controller.currentGreen)
        if direction is not None:
            self.last_green_end[direction] = engine.simulation_elapsed

    def red_time(self, engine, direction):
        current = engine.directionNumbers.get(engine.controller.currentGreen)
        if direction == current:
            return 0.0
        return engine.simulation_elapsed - self.last_green_end[direction]

    def starvation_guard_active(self, engine, observation, exclude_direction, params):
        limit = params.get("emergency_starvation_override_limit")
        if limit is None:
            return False
        return any(
            direction != exclude_direction
            and observation[direction]["queue_count"] > 0
            and self.red_time(engine, direction) > float(limit)
            for direction in self.DIRECTIONS
        )

    def emergency_eta(self, emergency, params):
        speed = float(params.get("emergency_speed_px_per_s", 80.0))
        headway = float(params.get("seconds_per_vehicle_ahead", 1.0))
        return emergency["distance"] / speed + emergency.get("vehicles_ahead", 0) * headway

    def find_priority_emergency(self, engine, observation, params, exclude_direction=None):
        if not bool(params.get("emergency_priority_enabled", True)):
            return None, None
        candidates = [
            (observation[direction]["emergency"]["distance"], direction)
            for direction in self.DIRECTIONS
            if direction != exclude_direction and observation[direction]["emergency"] is not None
        ]
        if not candidates:
            return None, None
        _distance, direction = min(candidates)
        if self.starvation_guard_active(engine, observation, direction, params):
            return None, None
        return direction, observation[direction]["emergency"]

    def should_preempt(self, engine, params, current_direction, elapsed_green_seconds):
        if elapsed_green_seconds < int(params.get("min_green", 5)):
            return False
        direction, _emergency = self.find_priority_emergency(
            engine, self.observation(engine), params, exclude_direction=current_direction
        )
        return direction is not None

    def get_green_extension(self, engine, params, current_direction, remaining_green):
        if not bool(params.get("emergency_priority_enabled", True)):
            return 0
        if remaining_green > float(params.get("emergency_extension_check_threshold", 2.0)):
            return 0

        emergency = self.observation(engine)[current_direction]["emergency"]
        if emergency is None:
            return 0

        if self.hold_direction != current_direction:
            self.hold_direction = current_direction
            self.hold_total = 0.0

        budget = float(params.get("emergency_max_hold_time", 20.0)) - self.hold_total
        needed = (
            self.emergency_eta(emergency, params)
            + float(params.get("emergency_clearance_buffer", 2.0))
            - remaining_green
        )
        if needed <= 0 or needed > budget:
            return 0

        extension = int(round(needed))
        self.hold_total += extension
        return extension

    def direction_debug(self, engine, observation, chosen, indices=None, emergency_direction=None):
        indices = indices or {}
        return {
            direction: {
                "queue": observation[direction]["queue_count"],
                "active": observation[direction]["queue_count"] > 0,
                "score": round(indices[direction], 2) if direction in indices else None,
                "excess_wait": None,
                "discharge_rate": None,
                "served_this_cycle": direction in self.served_directions,
                "chosen": direction == chosen,
                "emergency": direction == emergency_direction,
            }
            for direction in self.DIRECTIONS
        }

    def choose_next_phase(self, state, params, engine):
        observation = self.observation(engine)
        min_green = int(params.get("min_green", 5))
        max_green = int(params.get("max_green", 30))

        emergency_direction, emergency = self.find_priority_emergency(engine, observation, params)
        if emergency_direction is not None:
            eta = self.emergency_eta(emergency, params)
            buffer = float(params.get("emergency_clearance_buffer", 2.0))
            green_time = int(max(min_green, min(max_green, round(eta + buffer))))
            reason = (
                f"{emergency_direction.upper()} selected by Camera Queue Strategy: "
                f"{emergency['type']} detected {emergency['distance']:.0f}px from the stop line, "
                f"{emergency.get('vehicles_ahead', 0)} vehicle(s) ahead, estimated eta={eta:.1f}s, "
                f"green_time={green_time}s."
            )
            return (
                emergency_direction,
                green_time,
                reason,
                {
                    "emergency_priority": True,
                    "direction_debug": self.direction_debug(
                        engine, observation, emergency_direction, emergency_direction=emergency_direction
                    ),
                    "score_semantics": self.score_semantics,
                },
            )

        queues = {d: float(observation[d]["queue_count"]) for d in self.DIRECTIONS}
        active = [d for d in self.DIRECTIONS if queues[d] > 0]

        if not active:
            fallback = engine.directionNumbers.get(engine.controller.currentGreen) or self.DIRECTIONS[0]
            return (
                fallback,
                min_green,
                "No queue visible on any approach; holding current direction at minimum green.",
                {
                    "emergency_priority": False,
                    "direction_debug": self.direction_debug(engine, observation, fallback),
                    "score_semantics": self.score_semantics,
                },
            )

        if self.served_directions and set(active).issubset(self.served_directions):
            self.served_directions = set()

        fairness_lambda = float(params.get("fairness_lambda", 1.5))
        soft_limit = float(params.get("starvation_soft_limit", 20))
        indices = {
            d: queues[d] + fairness_lambda * max(0.0, self.red_time(engine, d) - soft_limit)
            for d in active
        }

        best = max(active, key=lambda d: indices[d])
        cycle_note = ""
        if bool(params.get("cycle_fairness_enabled", True)):
            unserved = [d for d in active if d not in self.served_directions]
            if unserved and best not in unserved:
                redirected = max(unserved, key=lambda d: indices[d])
                cycle_note = (
                    f" Cycle-fairness: {best.upper()} already served this cycle, "
                    f"redirected to unserved {redirected.upper()}."
                )
                best = redirected

        discharge_rate = float(params.get("assumed_discharge_rate", 0.5))
        raw_green = queues[best] / discharge_rate
        if observation[best]["is_saturated"]:
            # The queue reaches the edge of the frame, so the visible count
            # is only a lower bound.
            raw_green += float(params.get("saturated_green_bonus", 0.0))

        if len(active) <= 1:
            cap = max_green
        else:
            cap = min(max_green, float(params.get("multi_direction_max_green", 6)))
            exponent = float(params.get("demand_share_scaling_exponent", 0.0))
            total = sum(queues[d] for d in active)
            if exponent > 0 and total > 0:
                share_ratio = (queues[best] / total) * len(active)
                cap = min(max_green, cap * math.pow(share_ratio, exponent))

        green_time = int(max(min_green, min(cap, round(raw_green))))
        reason = (
            f"{best.upper()} selected by Camera Queue Strategy. "
            f"index={indices[best]:.2f} (visible queue={queues[best]:.0f}, "
            f"red_time={self.red_time(engine, best):.0f}s"
            f"{', queue reaches frame edge' if observation[best]['is_saturated'] else ''}), "
            f"green_time={green_time}s (clamped to [{min_green},{int(cap)}])."
            f"{cycle_note}"
        )
        return (
            best,
            green_time,
            reason,
            {
                "emergency_priority": False,
                "direction_debug": self.direction_debug(engine, observation, best, indices),
                "score_semantics": self.score_semantics,
            },
        )
