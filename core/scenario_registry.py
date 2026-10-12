import re
import time
from typing import Dict, List, Optional

from core.config_defaults import (
    default_scenarios,
    default_scenario_config,
    deep_copy_config,
)
from core.paths import SCENARIOS_FILE
from core.persistence import read_json, write_json


class ScenarioRegistry:
    def __init__(self):
        self._scenarios: List[Dict] = read_json(SCENARIOS_FILE, default_scenarios())

        if not self._scenarios:
            self._scenarios = default_scenarios()
            self.save()

        self._migrate_scenarios_if_needed()

    def _migrate_config(self, config: Dict) -> Dict:
        default_config = default_scenario_config()
        migrated = deep_copy_config(config)

        if "emergency" not in migrated:
            migrated["emergency"] = deep_copy_config(default_config["emergency"])

        if "vehicle_speeds" not in migrated:
            migrated["vehicle_speeds"] = deep_copy_config(default_config["vehicle_speeds"])
        else:
            for vehicle_type, speed in default_config["vehicle_speeds"].items():
                migrated["vehicle_speeds"].setdefault(vehicle_type, speed)

        return migrated

    def _migrate_scenarios_if_needed(self):
        changed = False

        for idx, scenario in enumerate(self._scenarios):
            original_config = scenario.get("config", {})
            migrated_config = self._migrate_config(original_config)

            if migrated_config != original_config:
                self._scenarios[idx]["config"] = migrated_config
                self._scenarios[idx]["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                changed = True

        if changed:
            self.save()

    def list_all(self) -> List[Dict]:
        return [deep_copy_config(x) for x in self._scenarios]

    def get_by_id(self, scenario_id: str) -> Optional[Dict]:
        for scenario in self._scenarios:
            if scenario["scenario_id"] == scenario_id:
                return deep_copy_config(scenario)
        return None

    def get_by_name(self, scenario_name: str) -> Optional[Dict]:
        for scenario in self._scenarios:
            if scenario["scenario_name"] == scenario_name:
                return deep_copy_config(scenario)
        return None

    def save(self) -> None:
        write_json(SCENARIOS_FILE, self._scenarios)

    def _slugify(self, text: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower()).strip("_")
        return slug or "scenario"

    def create_or_update(
        self,
        scenario_name: str,
        description: str,
        config: Dict,
        is_locked: bool = True,
        scenario_id: Optional[str] = None,
    ) -> Dict:
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        migrated_config = self._migrate_config(config)

        existing = self.get_by_id(scenario_id) if scenario_id else self.get_by_name(scenario_name)

        if existing:
            for idx, item in enumerate(self._scenarios):
                if item["scenario_id"] == existing["scenario_id"]:
                    self._scenarios[idx]["scenario_name"] = scenario_name
                    self._scenarios[idx]["description"] = description
                    self._scenarios[idx]["config"] = deep_copy_config(migrated_config)
                    self._scenarios[idx]["is_locked"] = is_locked
                    self._scenarios[idx]["updated_at"] = now
                    self.save()
                    return deep_copy_config(self._scenarios[idx])

        base_id = self._slugify(scenario_name)
        new_id = base_id
        counter = 2

        while self.get_by_id(new_id) is not None:
            new_id = f"{base_id}_{counter}"
            counter += 1

        scenario = {
            "scenario_id": new_id,
            "scenario_name": scenario_name,
            "description": description,
            "is_default": False,
            "is_locked": is_locked,
            "config": deep_copy_config(migrated_config),
            "created_at": now,
            "updated_at": now,
        }

        self._scenarios.append(scenario)
        self.save()
        return deep_copy_config(scenario)

    def delete(self, scenario_id: str) -> bool:
        kept = []
        deleted = False

        for item in self._scenarios:
            if item["scenario_id"] == scenario_id and not item.get("is_default", False):
                deleted = True
                continue
            kept.append(item)

        self._scenarios = kept

        if deleted:
            self.save()

        return deleted