import pygame

from simulation.camera import FRAME_SIZE
from state_providers.base_provider import BaseStateProvider

DIRECTIONS = ["right", "down", "left", "up"]


class GroundTruthStateProvider(BaseStateProvider):
    """Traffic state read directly from the simulation.

    Reports the same observation as the YOLO provider, for the same field
    of view (the 900x900 frame), but without detection errors and without
    an observation interval. It is the upper bound a camera could reach.
    """

    ACTIVE_LANES = [1, 2]
    # A standing vehicle this close to the frame edge means the queue
    # probably continues out of view.
    EDGE_MARGIN = 70.0
    # A vehicle entering the frame counts once this share of it is in view.
    MIN_VISIBLE_SHARE = 0.3

    def _vehicles_in_view(self, direction):
        """Vehicles on the approach: mostly inside the frame and with the
        centre before the stop line, the same area the camera assigns to
        this approach."""
        stop_line = self.engine.stopLines[direction]
        frame = pygame.Rect(0, 0, FRAME_SIZE, FRAME_SIZE)
        vehicles = []
        for lane in self.ACTIVE_LANES:
            for vehicle in self.engine.vehicles[direction][lane]:
                rect = vehicle.image.get_rect(topleft=(vehicle.x, vehicle.y))
                visible = rect.clip(frame)
                if visible.width * visible.height < self.MIN_VISIBLE_SHARE * rect.width * rect.height:
                    continue
                cx, cy = rect.center
                axis, sign = vehicle.HEADING[direction]
                if sign * (stop_line - (cx if axis == "x" else cy)) >= 0:
                    vehicles.append(vehicle)
        return vehicles

    def get_observation(self):
        observation = {}
        for direction in DIRECTIONS:
            stop_line = self.engine.stopLines[direction]
            vehicles = self._vehicles_in_view(direction)
            info = {
                "queue_count": 0,
                "visible_count": len(vehicles),
                "is_saturated": False,
                "emergency": None,
            }

            distances = []
            for vehicle in vehicles:
                heading = vehicle.HEADING[direction]
                distance = max(0.0, vehicle.distance_ahead(heading, stop_line))
                distances.append(distance)

                if vehicle.velocity == 0:
                    info["queue_count"] += 1
                    rear = vehicle.rear(heading)
                    to_edge = rear if heading[1] > 0 else FRAME_SIZE - rear
                    if to_edge <= self.EDGE_MARGIN:
                        info["is_saturated"] = True

                if vehicle.isEmergency and (
                    info["emergency"] is None or distance < info["emergency"]["distance"]
                ):
                    info["emergency"] = {
                        "type": vehicle.emergencyType,
                        "distance": distance,
                        "stopped": vehicle.velocity == 0,
                    }

            if info["emergency"] is not None:
                # Vehicles between the emergency vehicle and the stop line.
                info["emergency"]["vehicles_ahead"] = sum(
                    1 for distance in distances if distance < info["emergency"]["distance"]
                )
            observation[direction] = info
        return observation

    def get_state(self):
        observation = self.get_observation()
        return {direction: observation[direction]["visible_count"] for direction in DIRECTIONS}

    def get_rich_state(self):
        observation = self.get_observation()
        return {
            direction: {
                "queue_count": info["queue_count"],
                "visible_count": info["visible_count"],
                "score": None,
                "queue_level": None,
                "is_saturated": info["is_saturated"],
                "occupancy_ratio": None,
                "color": (230, 230, 230),
            }
            for direction, info in observation.items()
        }
