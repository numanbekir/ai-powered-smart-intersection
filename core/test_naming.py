import re
from typing import Dict

from core.paths import TEST_COUNTERS_FILE
from core.persistence import read_json, write_json


def scenario_prefix(scenario_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", scenario_name.upper())
    return (cleaned[:3] or "TST").ljust(3, "X")


class TestNameGenerator:
    def __init__(self):
        self._counters: Dict[str, int] = read_json(TEST_COUNTERS_FILE, {})

    def save(self):
        write_json(TEST_COUNTERS_FILE, self._counters)

    def reset(self):
        self._counters = {}
        self.save()

    def next_name(self, scenario_name: str) -> str:
        prefix = scenario_prefix(scenario_name)
        current = int(self._counters.get(prefix, 0)) + 1
        self._counters[prefix] = current
        self.save()
        return f"{prefix}-{current:03d}" if current <= 999 else f"{prefix}-{current}"