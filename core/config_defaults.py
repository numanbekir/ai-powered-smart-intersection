import copy
import time
from typing import Any, Dict, List


def now_str() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def default_vehicle_distribution(bike_enabled: bool = False) -> Dict[str, int]:
    if bike_enabled:
        return {"car": 50, "bus": 25, "truck": 20, "bike": 5}
    return {"car": 50, "bus": 25, "truck": 25, "bike": 0}


def default_emergency_config() -> Dict[str, Any]:
    return {
        "enabled": False,
        "vehicle_types": {
            "ambulance": True,
            "police": True,
            "firetruck": True,
        },
        "spawn_probability": 0.03,
        "min_spawn_gap": 20,
        "max_active_emergency": 1,
        "priority_enabled": True,
        "priority_green_time": 12,
    }


def default_scenario_config() -> Dict[str, Any]:
    per_road_dist = default_vehicle_distribution(False)

    return {
        "fps": 60,
        "simulation_time": 120,
        "playback_speed": 1.0,
        # v/c (talep/kapasite) ~0.55 -- olculmus doygun sistem kapasitesi
        # (~0.478 arac/sn, gercek kavsak kayitlariyla kalibre edilmis; bkz.
        # docs/scenario_capacity_calibration.md) uzerinden "dengeli/orta" bir
        # varsayilan. 1.0 (v/c~0.90, fiilen peak) DEGILDI.
        "spawn_interval": 1.82,
        "random_seed": 42,
        "allowed_vehicle_types": {
            "car": True,
            "bus": True,
            "truck": True,
            "bike": False,
        },
        "vehicle_speeds": {
            "car": 1.25,
            "bus": 1.30,
            "truck": 1.10,
            "bike": 1.50,
            "ambulance": 1.65,
            "police": 1.70,
            "firetruck": 1.35,
        },
        "direction_density": {
            "right": 25,
            "down": 25,
            "left": 25,
            "up": 25,
        },
        "road_vehicle_distribution": {
            "right": dict(per_road_dist),
            "down": dict(per_road_dist),
            "left": dict(per_road_dist),
            "up": dict(per_road_dist),
        },
        "lane_turn_policy": {
            "1": ["straight", "left"],
            "2": ["straight", "right"],
        },
        "left_turn_probability": 0.25,
        "right_turn_probability": 0.25,
        "fixed": {
            "initial_green": "right",
            "green_time": 10,
            "yellow_time": 3,
            "red_time": 50,
        },
        "emergency": default_emergency_config(),
    }


ADAPTIVE_PARAMS: Dict[str, Any] = {
    "min_green": 5,
    "max_green": 30,
    "yellow_time": 3,
    # Direction choice
    "fairness_lambda": 1.5,
    "starvation_soft_limit": 20,
    # Green time
    "startup_time": 2.0,
    "discharge_rate": 1.0,
    "saturated_green_bonus": 3.0,
    # Emergency vehicles
    "emergency_priority_enabled": True,
    "emergency_speed_px_per_s": 80.0,
    "seconds_per_vehicle_ahead": 1.0,
    "emergency_clearance_buffer": 2.0,
    "emergency_max_hold_time": 20.0,
    "emergency_extension_check_threshold": 2.0,
    "emergency_starvation_override_limit": 90.0,
}


def default_controller_versions() -> List[Dict[str, Any]]:
    """The two adaptive controllers. Both run the same decision rule with
    the same parameters. They differ only in the state provider that
    observes the intersection."""
    now = now_str()

    def version(version_id, display_name, provider_type, description, description_tr):
        return {
            "version_id": version_id,
            "display_name": display_name,
            "description": description,
            "description_tr": description_tr,
            "controller_family": "adaptive",
            "status": "active",
            "parent_version_id": None,
            "strategy_key": "demand",
            "implementation_key": "adaptive_controller",
            "target_state_provider_type": provider_type,
            "compatible_state_provider_types": [provider_type],
            "supports_real_preemption": True,
            "supports_cycle_fairness": True,
            "params": copy.deepcopy(ADAPTIVE_PARAMS),
            "created_at": now,
            "updated_at": now,
        }

    return [
        version(
            "adaptive_ground_truth",
            "Adaptif - Tam Bilgi",
            "ground_truth",
            "Adaptive rule fed with the exact vehicles on each approach, read from the "
            "simulation. The upper bound a camera could reach.",
            "Adaptif karar kuralı, her yöndeki araçları simülasyondan hatasız okuyarak "
            "çalışır. Bir kameranın ulaşabileceği üst sınırdır.",
        ),
        version(
            "adaptive_camera",
            "Adaptif - Kamera (YOLO)",
            "yolo",
            "The same adaptive rule fed only with what the YOLO detector sees on the "
            "overhead camera frame.",
            "Aynı adaptif karar kuralı, yalnızca YOLO modelinin üstten kamera karesinde "
            "tespit ettikleriyle çalışır.",
        ),
    ]


def default_state_providers() -> List[Dict[str, Any]]:
    now = now_str()

    return [
        {
            "provider_id": "ground_truth_v1",
            "display_name": "Ground Truth Provider V1",
            "provider_type": "ground_truth",
            "status": "active",
            "description": "Reads the vehicles on each approach directly from the simulation state, within the 900x900 frame.",
            "created_at": now,
        },
        {
            "provider_id": "yolo_v1",
            "display_name": "YOLO Provider",
            "provider_type": "yolo",
            "status": "active",
            "description": (
                "Detects vehicles on the overhead camera frame with a YOLO model trained on "
                "simulation frames. Reports standing vehicles per approach and detected "
                "emergency vehicles. Sees only the 900x900 frame."
            ),
            "created_at": now,
        },
    ]


def default_scenarios() -> List[Dict[str, Any]]:
    now = now_str()

    return [
        {
            "scenario_id": "default_scenario",
            "scenario_name": "Default Scenario",
            "description": "Editable fallback scenario used when no saved custom scenario is selected.",
            "is_default": True,
            "is_locked": False,
            "config": default_scenario_config(),
            "created_at": now,
            "updated_at": now,
        }
    ]


def default_app_state() -> Dict[str, Any]:
    return {
        "selected_scenario_id": "default_scenario",
        "selected_controller_version_id": "adaptive_ground_truth",
        "selected_state_provider_id": "ground_truth_v1",
        "emergency_priority_enabled": True,
        "cycle_fairness_enabled": True,
        "language": "en",
    }


def deep_copy_config(config: Dict[str, Any]) -> Dict[str, Any]:
    return copy.deepcopy(config)