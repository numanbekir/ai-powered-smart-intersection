import copy
import time
from typing import Dict, List, Optional

from core.config_defaults import default_controller_versions
from core.paths import CONTROLLER_VERSIONS_FILE
from core.persistence import read_json, write_json


class ControllerVersionRegistry:
    def __init__(self):
        self._versions: List[Dict] = read_json(
            CONTROLLER_VERSIONS_FILE,
            default_controller_versions()
        )
        if not self._versions:
            self._versions = default_controller_versions()
            self.save()

    def save(self):
        write_json(CONTROLLER_VERSIONS_FILE, self._versions)

    def list_all(self) -> List[Dict]:
        return copy.deepcopy(self._versions)

    def list_by_provider_type(self, provider_type: str) -> List[Dict]:
        matched = []

        for version in self._versions:
            target = version.get("target_state_provider_type", "ground_truth")

            compatible = version.get("compatible_state_provider_types")
            if compatible and provider_type in compatible:
                matched.append(version)
                continue

            if target == provider_type:
                matched.append(version)

        return copy.deepcopy(matched)

    def get(self, version_id: str) -> Optional[Dict]:
        for item in self._versions:
            if item["version_id"] == version_id:
                return copy.deepcopy(item)
        return None

    def get_latest(self) -> Dict:
        return copy.deepcopy(self._versions[-1])

    def create(self, version: Dict) -> Dict:
        if self.get(version["version_id"]):
            raise ValueError(f"Version already exists: {version['version_id']}")

        version = copy.deepcopy(version)
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        version.setdefault("created_at", now)
        version.setdefault("updated_at", now)

        self._versions.append(version)
        self.save()
        return copy.deepcopy(version)

    def update(self, version_id: str, updates: Dict) -> Dict:
        for idx, item in enumerate(self._versions):
            if item["version_id"] == version_id:
                updated = copy.deepcopy(item)
                updated.update(copy.deepcopy(updates))
                updated["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                self._versions[idx] = updated
                self.save()
                return copy.deepcopy(updated)

        raise ValueError(f"Version not found: {version_id}")

    def duplicate(
        self,
        parent_version_id: str,
        new_version_id: str,
        display_name: str,
        change_summary: str,
        rationale: str
    ) -> Dict:
        parent = self.get(parent_version_id)
        if not parent:
            raise ValueError(f"Parent version not found: {parent_version_id}")

        dup = copy.deepcopy(parent)
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        dup["version_id"] = new_version_id
        dup["display_name"] = display_name
        dup["parent_version_id"] = parent_version_id
        dup["change_summary"] = change_summary
        dup["rationale"] = rationale
        dup["created_at"] = now
        dup["updated_at"] = now

        return self.create(dup)