import copy
from typing import Dict, List, Optional

from core.config_defaults import default_state_providers
from core.paths import STATE_PROVIDERS_FILE
from core.persistence import read_json, write_json


class StateProviderRegistry:
    def __init__(self):
        self._providers = read_json(STATE_PROVIDERS_FILE, default_state_providers())
        if not self._providers:
            self._providers = default_state_providers()
            self.save()

    def save(self):
        write_json(STATE_PROVIDERS_FILE, self._providers)

    def list_all(self) -> List[Dict]:
        return copy.deepcopy(self._providers)

    def get(self, provider_id: str) -> Optional[Dict]:
        for item in self._providers:
            if item["provider_id"] == provider_id:
                return copy.deepcopy(item)
        return None
