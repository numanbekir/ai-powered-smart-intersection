from core.i18n import approach_name, t

DIRECTIONS = ["right", "down", "left", "up"]


class DemandStrategy:
    """The adaptive decision rule.

    Every input is an observation of the four approaches: how many vehicles
    are on each one, whether the queue reaches the edge of the view, and the
    nearest emergency vehicle. The rule never reads the simulation itself,
    so the same code runs on exact counts (ground truth provider) and on
    camera detections (YOLO provider). The difference between the two is
    the cost of perceiving the intersection through a camera.

    Direction: index = vehicles on the approach + lambda * red time beyond a
        soft limit. Within one cycle every approach with demand is served
        once before any approach is served again.
    Green time: start-up time + vehicles / discharge rate, the time the
        vehicles on the approach need to get through, between the minimum
        and the maximum green.
    Emergency: the approach with the nearest emergency vehicle is served
        first, for as long as the vehicle needs to reach the stop line.
    """

    strategy_key = "demand"
    score_semantics = {"label": "index (vehicles + λ·red time)", "higher_is_better": True}

    def __init__(self):
        self.served_directions = set()
        self.last_green_end = {direction: 0.0 for direction in DIRECTIONS}
        self.hold_direction = None
        self.hold_total = 0.0

    # --- Bookkeeping, driven by the controller -------------------------

    def phase_started(self, direction):
        self.served_directions.add(direction)

    def phase_ended(self, direction, now):
        self.last_green_end[direction] = now

    def red_time(self, direction, now, current_direction):
        if direction == current_direction:
            return 0.0
        return now - self.last_green_end[direction]

    # --- Emergency vehicles ----------------------------------------------

    def emergency_eta(self, emergency, params):
        speed = float(params["emergency_speed_px_per_s"])
        per_vehicle = float(params["seconds_per_vehicle_ahead"])
        return emergency["distance"] / speed + emergency["vehicles_ahead"] * per_vehicle

    def another_direction_starving(self, observation, params, now, current_direction, exclude):
        limit = float(params["emergency_starvation_override_limit"])
        return any(
            direction != exclude
            and observation[direction]["visible_count"] > 0
            and self.red_time(direction, now, current_direction) > limit
            for direction in DIRECTIONS
        )

    def find_priority_emergency(self, observation, params, now, current_direction, exclude=None):
        """The approach whose emergency vehicle is nearest to its stop line.
        Priority is skipped while another approach has been red for too
        long, so a stuck emergency vehicle cannot starve the rest."""
        if not params.get("emergency_priority_enabled", True):
            return None
        candidates = [
            (observation[direction]["emergency"]["distance"], direction)
            for direction in DIRECTIONS
            if direction != exclude and observation[direction]["emergency"] is not None
        ]
        if not candidates:
            return None
        _distance, direction = min(candidates)
        if self.another_direction_starving(observation, params, now, current_direction, direction):
            return None
        return direction

    def should_preempt(self, observation, params, now, current_direction, elapsed_green):
        """Cut the running green short for an emergency vehicle on another
        approach. A green is never cut before its minimum time."""
        if elapsed_green < int(params["min_green"]):
            return False
        return (
            self.find_priority_emergency(
                observation, params, now, current_direction, exclude=current_direction
            )
            is not None
        )

    def green_extension(self, observation, params, current_direction, remaining_green):
        """Seconds to hold a green that is about to end, so an emergency
        vehicle on this approach gets through. Zero when it would not make
        it within the hold budget anyway."""
        if not params.get("emergency_priority_enabled", True):
            return 0
        if remaining_green > float(params["emergency_extension_check_threshold"]):
            return 0

        emergency = observation[current_direction]["emergency"]
        if emergency is None:
            return 0

        if self.hold_direction != current_direction:
            self.hold_direction = current_direction
            self.hold_total = 0.0

        budget = float(params["emergency_max_hold_time"]) - self.hold_total
        needed = (
            self.emergency_eta(emergency, params)
            + float(params["emergency_clearance_buffer"])
            - remaining_green
        )
        if needed <= 0 or needed > budget:
            return 0

        extension = int(round(needed))
        self.hold_total += extension
        return extension

    # --- Normal traffic --------------------------------------------------

    def rank(self, observation, params, now, current_direction):
        """Pick the next approach without changing any state. Returns
        (direction, indices, served set to carry on with, note)."""
        demand = {d: float(observation[d]["visible_count"]) for d in DIRECTIONS}
        active = [d for d in DIRECTIONS if demand[d] > 0]
        if not active:
            return None, {}, self.served_directions, ""

        served = self.served_directions
        if served and set(active) <= served:
            served = set()

        fairness_lambda = float(params["fairness_lambda"])
        soft_limit = float(params["starvation_soft_limit"])
        indices = {
            d: demand[d]
            + fairness_lambda * max(0.0, self.red_time(d, now, current_direction) - soft_limit)
            for d in active
        }

        best = max(active, key=lambda d: indices[d])
        note = ""
        if params.get("cycle_fairness_enabled", True):
            unserved = [d for d in active if d not in served]
            if unserved and best not in unserved:
                redirected = max(unserved, key=lambda d: indices[d])
                note = t("sim.reason.fairness_note")
                best = redirected
        return best, indices, served, note

    def green_time_for(self, observation, params, direction):
        info = observation[direction]
        needed = float(params["startup_time"]) + info["visible_count"] / float(
            params["discharge_rate"]
        )
        if info["is_saturated"]:
            # The queue reaches the edge of the view, so the count is only
            # a lower bound.
            needed += float(params["saturated_green_bonus"])
        return int(max(int(params["min_green"]), min(int(params["max_green"]), round(needed))))

    def direction_debug(self, observation, chosen, indices=None, emergency_direction=None):
        indices = indices or {}
        return {
            direction: {
                "queue": observation[direction]["visible_count"],
                "active": observation[direction]["visible_count"] > 0,
                "score": round(indices[direction], 2) if direction in indices else None,
                "excess_wait": None,
                "discharge_rate": None,
                "served_this_cycle": direction in self.served_directions,
                "chosen": direction == chosen,
                "emergency": direction == emergency_direction,
            }
            for direction in DIRECTIONS
        }

    def choose_next_phase(self, observation, params, now, current_direction):
        """Returns (direction, green_time, reason, meta)."""
        min_green = int(params["min_green"])
        max_green = int(params["max_green"])

        emergency_direction = self.find_priority_emergency(
            observation, params, now, current_direction
        )
        if emergency_direction is not None:
            emergency = observation[emergency_direction]["emergency"]
            eta = self.emergency_eta(emergency, params)
            green_time = int(
                max(
                    min_green,
                    min(max_green, round(eta + float(params["emergency_clearance_buffer"]))),
                )
            )
            reason = t(
                "sim.reason.emergency",
                approach=approach_name(emergency_direction),
                green=green_time,
                distance=f"{emergency['distance']:.0f}",
                ahead=emergency["vehicles_ahead"],
            )
            return (
                emergency_direction,
                green_time,
                reason,
                {
                    "emergency_priority": True,
                    "direction_debug": self.direction_debug(
                        observation, emergency_direction, emergency_direction=emergency_direction
                    ),
                    "score_semantics": self.score_semantics,
                },
            )

        best, indices, served, note = self.rank(observation, params, now, current_direction)
        if best is None:
            fallback = current_direction or DIRECTIONS[0]
            return (
                fallback,
                min_green,
                t("sim.reason.no_demand", approach=approach_name(fallback)),
                {
                    "emergency_priority": False,
                    "direction_debug": self.direction_debug(observation, fallback),
                    "score_semantics": self.score_semantics,
                },
            )

        self.served_directions = served
        green_time = self.green_time_for(observation, params, best)
        info = observation[best]
        reason = t(
            "sim.reason.normal",
            approach=approach_name(best),
            green=green_time,
            count=info["visible_count"],
            red=f"{self.red_time(best, now, current_direction):.0f}",
            note=note,
        )
        return (
            best,
            green_time,
            reason,
            {
                "emergency_priority": False,
                "direction_debug": self.direction_debug(observation, best, indices),
                "score_semantics": self.score_semantics,
            },
        )

    def preview_next_direction(self, engine, params):
        """Read-only estimate for the panel: the approach that would be
        chosen if the current green ended now."""
        observation = engine.controller.state_provider.get_observation()
        current_direction = engine.get_current_green_direction()
        now = engine.simulation_elapsed
        emergency_direction = self.find_priority_emergency(
            observation, params, now, current_direction, exclude=current_direction
        )
        if emergency_direction is not None:
            return emergency_direction
        best, _indices, _served, _note = self.rank(observation, params, now, current_direction)
        return best
