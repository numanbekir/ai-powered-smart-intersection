from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Scenario:
    scenario_id: str
    scenario_name: str
    description: str
    is_default: bool
    is_locked: bool
    config: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Scenario":
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "description": self.description,
            "is_default": self.is_default,
            "is_locked": self.is_locked,
            "config": self.config,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
