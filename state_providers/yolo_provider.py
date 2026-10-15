import threading
import time
from pathlib import Path

import pygame

import numpy as np

from simulation.camera import CLASS_NAMES, FRAME_SIZE, IntersectionCamera
from state_providers.base_provider import BaseStateProvider

WEIGHTS_PATH = Path(__file__).resolve().parents[1] / "weights" / "vehicle_detector.pt"
EMERGENCY_CLASSES = {"ambulance", "police", "firetruck"}
DIRECTIONS = ["right", "down", "left", "up"]


class YoloStateProvider(BaseStateProvider):
    """Traffic state from YOLO detections on the overhead camera frame.

    Once per simulated second the camera frame is run through the detector.
    Each detection is assigned to an approach by its position. Every vehicle
    seen on an approach counts as demand, and it counts as queued when it
    has not moved since the previous observation.
    Nothing is read from the vehicles themselves: what is outside the frame,
    or missed by the detector, is unknown to the controller.
    """

    MODEL_NAME = "YOLO11n"
    OBSERVATION_INTERVAL = 1.0
    CONFIDENCE = 0.4
    IMAGE_SIZE = 896
    # A vehicle that moved less than this (px) between two observations is
    # standing. The slowest moving vehicle covers about 40 px in a second.
    STOPPED_TOLERANCE = 6.0
    # A standing vehicle this close to the frame edge means the queue
    # probably continues out of view.
    EDGE_MARGIN = 70.0
    DISPLAY_REFRESH_FRAMES = 3

    def __init__(self, engine):
        self.engine = engine
        self.camera = IntersectionCamera(engine)
        self.model = self._load_model()
        self.rois = self._build_rois()
        self.next_observation_time = 0.0
        self.previous_centers = {direction: [] for direction in DIRECTIONS}
        self.detections = []
        self.observation = {direction: self._empty_direction() for direction in DIRECTIONS}
        self._display_detections = []
        self._display_age = 0
        # Smoothed time of one detection pass, shown on the panel.
        self.inference_ms = 0.0
        self._model_lock = threading.Lock()
        self._display_thread = None
        self._display_request = threading.Event()
        self._display_frame = None
        engine.tick_listeners.append(self._on_tick)

    def _load_model(self):
        if not WEIGHTS_PATH.exists():
            raise FileNotFoundError(
                f"Detector weights not found: {WEIGHTS_PATH}. "
                "Run tools/generate_detection_dataset.py and tools/train_detector.py first."
            )
        try:
            import torch
            from ultralytics import YOLO
        except ImportError as error:
            raise ImportError(
                "The YOLO provider needs the packages in requirements-yolo.txt."
            ) from error

        self.device = 0 if torch.cuda.is_available() else "cpu"
        model = YOLO(str(WEIGHTS_PATH))
        # The first prediction loads the remaining torch modules. It has to
        # happen here, before the window opens: loading them after the
        # display is up crashes the process on X11.
        blank = np.zeros((FRAME_SIZE, FRAME_SIZE, 3), dtype=np.uint8)
        model.predict(blank, imgsz=self.IMAGE_SIZE, device=self.device, verbose=False)
        return model

    def _build_rois(self):
        # Entry half of each road, from the frame edge up to the stop line.
        # The centre lines of the two roads sit at 450 px.
        stop = self.engine.stopLines
        return {
            "right": {"x_min": 0, "x_max": stop["right"], "y_min": 450, "y_max": 512},
            "down": {"x_min": 375, "x_max": 450, "y_min": 0, "y_max": stop["down"]},
            "left": {"x_min": stop["left"], "x_max": FRAME_SIZE, "y_min": 388, "y_max": 450},
            "up": {"x_min": 450, "x_max": 527, "y_min": stop["up"], "y_max": FRAME_SIZE},
        }

    @staticmethod
    def _empty_direction():
        return {
            "queue_count": 0,
            "visible_count": 0,
            "is_saturated": False,
            "emergency": None,
        }

    def _direction_of(self, cx, cy):
        for direction, roi in self.rois.items():
            if roi["x_min"] <= cx <= roi["x_max"] and roi["y_min"] <= cy <= roi["y_max"]:
                return direction
        return None

    def _distance_to_stop_line(self, direction, box):
        x1, y1, x2, y2 = box
        stop = self.engine.stopLines[direction]
        if direction == "right":
            return stop - x2
        if direction == "down":
            return stop - y2
        if direction == "left":
            return x1 - stop
        return y1 - stop

    def _distance_to_frame_edge(self, direction, box):
        x1, y1, x2, y2 = box
        if direction == "right":
            return x1
        if direction == "down":
            return y1
        if direction == "left":
            return FRAME_SIZE - x2
        return FRAME_SIZE - y2

    def _predict(self, frame_rgb):
        frame = frame_rgb[:, :, ::-1]  # the detector expects BGR
        with self._model_lock:
            started = time.perf_counter()
            result = self.model.predict(
                frame,
                imgsz=self.IMAGE_SIZE,
                conf=self.CONFIDENCE,
                device=self.device,
                verbose=False,
            )[0]
            elapsed_ms = (time.perf_counter() - started) * 1000.0
        self.inference_ms = elapsed_ms if not self.inference_ms else (
            0.9 * self.inference_ms + 0.1 * elapsed_ms
        )
        boxes = result.boxes
        return [
            (CLASS_NAMES[int(cls)], float(conf), tuple(float(v) for v in xyxy))
            for cls, conf, xyxy in zip(boxes.cls.tolist(), boxes.conf.tolist(), boxes.xyxy.tolist())
        ]

    def _detect(self):
        return self._predict(self.camera.frame_rgb())

    def _on_tick(self, engine):
        if engine.simulation_elapsed < self.next_observation_time:
            return
        self.next_observation_time = engine.simulation_elapsed + self.OBSERVATION_INTERVAL
        self.observe()

    def observe(self):
        detections = self._detect()
        observation = {direction: self._empty_direction() for direction in DIRECTIONS}
        centers = {direction: [] for direction in DIRECTIONS}

        for name, _confidence, box in detections:
            cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
            direction = self._direction_of(cx, cy)
            if direction is None:
                continue

            info = observation[direction]
            info["visible_count"] += 1
            centers[direction].append((cx, cy))

            stopped = any(
                abs(cx - px) <= self.STOPPED_TOLERANCE and abs(cy - py) <= self.STOPPED_TOLERANCE
                for px, py in self.previous_centers[direction]
            )
            if stopped:
                info["queue_count"] += 1
                if self._distance_to_frame_edge(direction, box) <= self.EDGE_MARGIN:
                    info["is_saturated"] = True

            if name in EMERGENCY_CLASSES:
                distance = max(0.0, self._distance_to_stop_line(direction, box))
                if info["emergency"] is None or distance < info["emergency"]["distance"]:
                    info["emergency"] = {"type": name, "distance": distance, "stopped": stopped}

        for direction in DIRECTIONS:
            emergency = observation[direction]["emergency"]
            if emergency is not None:
                # Vehicles between the emergency vehicle and the stop line.
                emergency["vehicles_ahead"] = sum(
                    1
                    for name, _c, box in detections
                    if self._direction_of((box[0] + box[2]) / 2, (box[1] + box[3]) / 2) == direction
                    and max(0.0, self._distance_to_stop_line(direction, box)) < emergency["distance"]
                )

        self.previous_centers = centers
        self.detections = detections
        self.observation = observation

    def get_observation(self):
        return self.observation

    def get_state(self):
        observation = self.observation
        # Demand is every vehicle seen on the approach, standing or still
        # driving towards the stop line.
        return {direction: observation[direction]["visible_count"] for direction in DIRECTIONS}

    def detect_for_display(self):
        """Detections for drawing only. They are computed on a worker
        thread from a copy of the frame, so the window keeps its frame
        rate. The controller keeps using the once-per-second observation."""
        if self._display_thread is None:
            self._display_thread = threading.Thread(target=self._display_worker, daemon=True)
            self._display_thread.start()

        if self._display_age % self.DISPLAY_REFRESH_FRAMES == 0 and not self._display_request.is_set():
            self._display_frame = self.camera.render().copy()
            self._display_request.set()
        self._display_age += 1
        return self._display_detections

    def _display_worker(self):
        while self.engine.simulationRunning:
            if not self._display_request.wait(timeout=0.1):
                continue
            pixels = pygame.surfarray.array3d(self._display_frame)
            self._display_detections = self._predict(
                np.ascontiguousarray(pixels.transpose(1, 0, 2))
            )
            self._display_request.clear()

    def get_rich_state(self):
        observation = self.observation
        rich_state = {}
        for direction in DIRECTIONS:
            info = observation[direction]
            if info["is_saturated"]:
                level, color = "full", (235, 90, 90)
            elif info["queue_count"] > 0:
                level, color = "queue", (240, 190, 70)
            else:
                level, color = "empty", (120, 210, 140)
            rich_state[direction] = {
                "queue_count": info["queue_count"],
                "visible_count": info["visible_count"],
                "score": None,
                "queue_level": level,
                "is_saturated": info["is_saturated"],
                "occupancy_ratio": None,
                "color": color,
                "roi": self.rois[direction],
            }
        return rich_state
