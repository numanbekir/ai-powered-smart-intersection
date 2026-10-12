from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ControllerVersion:
    version_id: str
    display_name: str
    controller_family: str
    status: str
    parent_version_id: Optional[str]
    strategy_key: str
    implementation_key: str
    params: Dict[str, Any] = field(default_factory=dict)
    change_summary: str = ""
    rationale: str = ""
    expected_effect: str = ""
    created_at: str = ""
    updated_at: str = ""
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ControllerVersion":
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "display_name": self.display_name,
            "controller_family": self.controller_family,
            "status": self.status,
            "parent_version_id": self.parent_version_id,
            "strategy_key": self.strategy_key,
            "implementation_key": self.implementation_key,
            "params": self.params,
            "change_summary": self.change_summary,
            "rationale": self.rationale,
            "expected_effect": self.expected_effect,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags,
        }
