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
        "spawn_interval": 3.81,
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


def default_controller_versions() -> List[Dict[str, Any]]:
    now = now_str()

    return [
        {
            "version_id": "adaptive_optimal_ground_truth",
            "display_name": "Adaptive Optimal - Ground Truth (Queueing-Theory Based)",
            "controller_family": "adaptive",
            "status": "active",
            "parent_version_id": None,
            "strategy_key": "optimal_ground_truth",
            "implementation_key": "adaptive_controller",
            "target_state_provider_type": "ground_truth",
            "compatible_state_provider_types": ["ground_truth"],
            "params": {
                "min_green": 5,
                "max_green": 30,
                "yellow_time": 3,
                "fairness_lambda": 1.5,
                "starvation_soft_limit": 20,
                "min_effective_discharge_rate": 0.3,
                "emergency_clearance_buffer": 2.0,
                "emergency_max_hold_time": 20.0,
                "emergency_extension_check_threshold": 2.0,
                "multi_direction_max_green": 6,
                "controller_repeat_guard_enabled": False,
                "emergency_starvation_override_limit": 60.0,
            },
            "change_summary": "Queueing-theory based decision mechanism using ground truth's full-information advantage.",
            "rationale": "Direction/green-time selection from the c-mu rule + a Lagrange fairness constraint, with exact ETA-based emergency preemption/hold, instead of hand-tuned heuristic weights.",
            "expected_effect": "Outperforms fixed-time on average/tail wait across nearly all scenarios; ground_truth's single strategy and the oracle benchmark for evaluating imperfect-perception providers.",
            "created_at": now,
            "updated_at": now,
            "tags": ["adaptive", "optimal", "ground_truth", "queueing_theory"],
        },
        {
            "version_id": "adaptive_optimal_ground_truth_v2",
            "display_name": "Adaptive Optimal v2 - Ground Truth (Emergency Priority Switch)",
            "controller_family": "adaptive",
            "status": "active",
            "parent_version_id": "adaptive_optimal_ground_truth",
            "strategy_key": "optimal_ground_truth",
            "implementation_key": "adaptive_controller",
            "target_state_provider_type": "ground_truth",
            "compatible_state_provider_types": ["ground_truth"],
            "params": {
                "min_green": 5,
                "max_green": 30,
                "yellow_time": 3,
                "fairness_lambda": 1.5,
                "starvation_soft_limit": 20,
                "min_effective_discharge_rate": 0.3,
                "emergency_clearance_buffer": 2.0,
                "emergency_max_hold_time": 20.0,
                "emergency_extension_check_threshold": 2.0,
                "multi_direction_max_green": 6,
                "controller_repeat_guard_enabled": False,
                "emergency_priority_enabled": True,
                "emergency_starvation_override_limit": 90.0,
            },
            "change_summary": (
                "Same queueing-theory decision mechanism as v1, with an "
                "emergency_priority_enabled on/off switch and a loosened "
                "starvation-override guard (90s vs v1's 60s) when on."
            ),
            "rationale": (
                "Adds a documented emergency_priority_enabled toggle; when off, "
                "emergency vehicles get no special treatment and are handled as "
                "normal queue members. When on, a 90s guard was chosen after "
                "sweeping 90/120/150/180 on mixed_master_scenario: it keeps "
                "normal-traffic metrics within ~1-8% of v1 there while still "
                "beating v1's emergency wait time, and has zero measured effect "
                "on standard (shorter) scenarios since it never triggers within "
                "their duration."
            ),
            "expected_effect": (
                "Lower emergency wait times than v1 with no normal-traffic cost "
                "in standard scenarios; in sustained extreme-load scenarios "
                "(mixed_master_scenario) normal-traffic metrics stay close to "
                "v1's while emergency wait remains better than v1."
            ),
            "created_at": now,
            "updated_at": now,
            "tags": [
                "adaptive",
                "optimal",
                "ground_truth",
                "queueing_theory",
                "emergency_priority_switch",
                "v2",
            ],
        },
        {
            "version_id": "adaptive_optimal_ground_truth_v3",
            "display_name": "Adaptive Optimal v3 - Ground Truth (Demand-Share Duration Scaling)",
            "controller_family": "adaptive",
            "status": "active",
            "parent_version_id": "adaptive_optimal_ground_truth_v2",
            "strategy_key": "optimal_ground_truth",
            "implementation_key": "adaptive_controller",
            "target_state_provider_type": "ground_truth",
            "compatible_state_provider_types": ["ground_truth"],
            "params": {
                "min_green": 5,
                "max_green": 30,
                "yellow_time": 3,
                "fairness_lambda": 1.5,
                "starvation_soft_limit": 20,
                "min_effective_discharge_rate": 0.3,
                "emergency_clearance_buffer": 2.0,
                "emergency_max_hold_time": 20.0,
                "emergency_extension_check_threshold": 2.0,
                "multi_direction_max_green": 6,
                "controller_repeat_guard_enabled": False,
                "emergency_priority_enabled": True,
                "emergency_starvation_override_limit": 90.0,
                "demand_share_scaling_exponent": 0.5,
            },
            "change_summary": (
                "Same decision mechanism as v2, but the multi-direction green "
                "cap now scales with the selected direction's share of active "
                "demand instead of being flat -- a dominant queue is no longer "
                "capped at the same duration as a light one; balanced scenarios "
                "stay very close to v2 (share ~ even share -> ratio ~ 1)."
            ),
            "rationale": (
                "Live GUI observation: multi-direction green times were nearly "
                "always 5-6s regardless of queue size, since raw_green already "
                "exceeded the flat cap even for small (2-3 vehicle) queues -- a "
                "real gap in the 'adaptive' premise. Flatly raising the cap was "
                "tried earlier and made every scenario worse (it also inflated "
                "cycle length for lightly-loaded decisions). Scaling the cap by "
                "relative demand share avoids that failure mode. Swept "
                "0/0.5/1.0/1.5/2.0: aggregate avg+tail wait was best at 1.0, but "
                "balanced_traffic (meant to stay unaffected) regressed avg_wait "
                "+11.7% there, since even nominally-symmetric traffic has enough "
                "moment-to-moment queue imbalance for a strong exponent to "
                "overreact to. 0.5 was chosen: negligible balanced_traffic cost "
                "(+0.9%) while still capturing most of the asymmetric-scenario "
                "gain (right_heavy_traffic avg_wait -20%, asymmetric_peak_traffic "
                "-14%)."
            ),
            "expected_effect": (
                "Improved avg/tail wait in asymmetric, direction-dominant "
                "scenarios; near-identical results to v2 in balanced scenarios."
            ),
            "created_at": now,
            "updated_at": now,
            "tags": [
                "adaptive",
                "optimal",
                "ground_truth",
                "queueing_theory",
                "emergency_priority_switch",
                "demand_share_duration_scaling",
                "v3",
            ],
        },
        {
            "version_id": "adaptive_rolling_horizon_ground_truth",
            "display_name": "Adaptive Rolling-Horizon - Ground Truth (Multi-Phase Lookahead)",
            "controller_family": "adaptive",
            "status": "active",
            "parent_version_id": "adaptive_optimal_ground_truth_v3",
            "strategy_key": "rolling_horizon_ground_truth",
            "implementation_key": "adaptive_controller",
            "target_state_provider_type": "ground_truth",
            "compatible_state_provider_types": ["ground_truth"],
            "params": {
                "min_green": 5,
                "max_green": 30,
                "yellow_time": 3,
                "min_effective_discharge_rate": 0.3,
                "emergency_clearance_buffer": 2.0,
                "emergency_max_hold_time": 20.0,
                "emergency_extension_check_threshold": 2.0,
                "controller_repeat_guard_enabled": False,
                "emergency_priority_enabled": True,
                "emergency_starvation_override_limit": 90.0,
                "rolling_horizon_depth": 2,
                "rolling_horizon_arrival_rate_alpha": 0.35,
                "rolling_horizon_fairness_weight": 10.0,
            },
            "change_summary": (
                "Keeps v3's emergency handling unchanged (unconditional "
                "priority + 90s guard), but replaces the greedy single-step "
                "normal-traffic decision with a bounded 2-phase lookahead "
                "search scored by a quadratic queue cost plus a real-wait-time "
                "fairness term -- no separate cycle-fairness or "
                "duration-scaling heuristics."
            ),
            "rationale": (
                "v3 needed two separate patches (cycle-fairness, demand-share "
                "duration scaling) that kept trading off against each other -- "
                "a structural limit of greedy single-step decisions. A lookahead "
                "planner can weigh 'give this direction more green now' against "
                "'other queues grow while I do' directly, in one cost function. "
                "First version (queue^2 cost only) had a self-reinforcing "
                "starvation bug: discharge_rate is only learned for directions "
                "that actually get served, so a rarely-served direction stays "
                "at a low learned rate, which makes serving it look "
                "'inefficient' to the search, so it gets served even less. "
                "Fixed by adding a linear cost term on real (ground-truth) "
                "max_wait per direction, independent of the discharge_rate "
                "estimate. rolling_horizon_fairness_weight=10 chosen from a "
                "small sweep (right_heavy_traffic + balanced_traffic, 3 seeds)."
            ),
            "expected_effect": (
                "Comparable to v3 in balanced scenarios; better than v3 in "
                "non-linear/saturated regimes (mixed_master_scenario) where a "
                "short lookahead can see the cost of over-frequent phase "
                "switching. Unmeasured, to be validated."
            ),
            "created_at": now,
            "updated_at": now,
            "tags": [
                "adaptive",
                "rolling_horizon",
                "ground_truth",
                "mpc",
                "lookahead_planning",
                "emergency_priority_switch",
            ],
        },
        {
            "version_id": "adaptive_camera_queue_v1",
            "display_name": "Adaptive Camera Queue v1 - YOLO",
            "description": "Applies the decision rule of Adaptive Optimal v3 using only what the YOLO state provider detects on the overhead camera frame: visible standing vehicles per approach and detected emergency vehicles.",
            "controller_family": "adaptive",
            "status": "active",
            "parent_version_id": "adaptive_optimal_ground_truth_v3",
            "strategy_key": "camera_queue",
            "implementation_key": "adaptive_controller",
            "target_state_provider_type": "yolo",
            "compatible_state_provider_types": ["yolo"],
            "supports_real_preemption": True,
            "supports_cycle_fairness": True,
            "params": {
                "min_green": 5,
                "max_green": 30,
                "yellow_time": 3,
                "fairness_lambda": 1.5,
                "starvation_soft_limit": 20,
                "emergency_clearance_buffer": 2.0,
                "emergency_max_hold_time": 20.0,
                "emergency_extension_check_threshold": 2.0,
                "multi_direction_max_green": 6,
                "controller_repeat_guard_enabled": False,
                "emergency_priority_enabled": True,
                "emergency_starvation_override_limit": 90.0,
                "demand_share_scaling_exponent": 0.5,
                "assumed_discharge_rate": 0.5,
                "emergency_speed_px_per_s": 80.0,
                "seconds_per_vehicle_ahead": 1.0,
                "saturated_green_bonus": 0.0
            },
            "change_summary": "v3'ün karar kuralı, girdileri yalnızca kamera tespitlerinden ve kontrolcünün kendi saatinden alacak şekilde yeniden yazıldı. Araç konumu, hızı ve bekleme süresi simülasyondan okunmaz.",
            "rationale": "Tam bilgili v3 ile aynı kuralı kamera girdisiyle çalıştırmak, aradaki farkı algılamanın maliyeti olarak ölçmeyi sağlar: sınırlı görüş alanı, bir saniyelik gözlem aralığı ve tespit hataları.",
            "expected_effect": "Kuyruğun görüş alanına sığdığı senaryolarda v3'e yakın sonuç. Kuyruğun kare dışına taştığı yoğun senaryolarda v3'ün gerisinde.",
            "created_at": now,
            "updated_at": now,
            "tags": [
                "adaptive",
                "camera",
                "yolo",
                "object_detection",
                "real_preemption",
                "cycle_fairness"
            ],
            "description_tr": "Adaptive Optimal v3'ün karar kuralını yalnızca YOLO sağlayıcının üstten kamera karesinde tespit ettikleriyle uygular: her yönde görünen duran araçlar ve tespit edilen acil durum araçları."
        },
    ]


def default_state_providers() -> List[Dict[str, Any]]:
    now = now_str()

    return [
        {
            "provider_id": "ground_truth_v1",
            "display_name": "Ground Truth Provider V1",
            "provider_type": "ground_truth",
            "status": "active",
            "description": "Reads all waiting vehicles directly from simulation state.",
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
        "selected_controller_version_id": "adaptive_optimal_ground_truth",
        "selected_state_provider_id": "ground_truth_v1",
        "emergency_priority_enabled": True,
        "cycle_fairness_enabled": True,
        "repeat_guard_enabled": False,
        "language": "en",
    }


def deep_copy_config(config: Dict[str, Any]) -> Dict[str, Any]:
    return copy.deepcopy(config)