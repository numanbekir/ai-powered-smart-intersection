"""Overhead camera view of the intersection.

Renders the 900x900 simulation area (road, signals, vehicles) to an
off-screen surface, without the GUI panel or any debug overlay. The same
frame is used to build the detection dataset and to feed the YOLO state
provider, so the detector is trained on exactly what it sees at run time.
"""
import pygame

FRAME_SIZE = 900
CLASS_NAMES = ["car", "bus", "truck", "bike", "ambulance", "police", "firetruck"]
SIGNAL_ANGLES = [0, 90, 180, 270]


class IntersectionCamera:
    def __init__(self, engine):
        self.engine = engine
        self.surface = pygame.Surface((FRAME_SIZE, FRAME_SIZE))
        self.background = pygame.image.load(str(engine.images_dir / "intersection.png"))
        self.signals = {
            name: {
                angle: pygame.transform.rotate(
                    pygame.image.load(str(engine.images_dir / "signals" / f"{name}.png")),
                    angle,
                )
                for angle in SIGNAL_ANGLES
            }
            for name in ["red", "yellow", "green"]
        }

    def _signal_name(self, index):
        controller = self.engine.controller
        if index != controller.currentGreen:
            return "red"
        return "yellow" if controller.currentYellow == 1 else "green"

    def render(self):
        surface = self.surface
        surface.blit(self.background, (0, 0))

        for index, info in enumerate(self.engine.signalCoods):
            image = self.signals[self._signal_name(index)][info["angle"]]
            surface.blit(image, image.get_rect(center=info["pos"]).topleft)

        for vehicle in list(self.engine.simulation):
            if getattr(vehicle, "_placed", False):
                surface.blit(vehicle.image, (vehicle.x, vehicle.y))

        return surface

    def frame_rgb(self):
        """Current frame as an (H, W, 3) uint8 array."""
        import numpy as np

        pixels = pygame.surfarray.array3d(self.render())
        return np.ascontiguousarray(pixels.transpose(1, 0, 2))

    def vehicle_boxes(self, min_visible=0.5):
        """Ground-truth boxes of the vehicles inside the frame.

        Returns (class_name, x1, y1, x2, y2) tuples, clipped to the frame.
        Vehicles with less than min_visible of their area in view are left
        out, as a detector cannot be expected to find them.
        """
        boxes = []
        for vehicle in list(self.engine.simulation):
            if not getattr(vehicle, "_placed", False):
                continue
            rect = vehicle.image.get_rect()
            x1, y1 = vehicle.x, vehicle.y
            x2, y2 = x1 + rect.width, y1 + rect.height
            cx1, cy1 = max(0.0, x1), max(0.0, y1)
            cx2, cy2 = min(float(FRAME_SIZE), x2), min(float(FRAME_SIZE), y2)
            if cx2 <= cx1 or cy2 <= cy1:
                continue
            visible = (cx2 - cx1) * (cy2 - cy1) / float(rect.width * rect.height)
            if visible < min_visible:
                continue
            boxes.append((vehicle.vehicleClass, cx1, cy1, cx2, cy2))
        return boxes
