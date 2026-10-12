from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ExperimentResult:
    timestamp: str
    test_identity: Dict[str, Any]
    experiment_identity: Dict[str, Any]
    interrupted: bool
    metrics: Dict[str, Any] = field(default_factory=dict)
    per_direction: Dict[str, Any] = field(default_factory=dict)
    decision_log: List[Dict[str, Any]] = field(default_factory=list)
    config_snapshot: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "test_identity": self.test_identity,
            "experiment_identity": self.experiment_identity,
            "interrupted": self.interrupted,
            "metrics": self.metrics,
            "per_direction": self.per_direction,
            "decision_log": self.decision_log,
            "config_snapshot": self.config_snapshot,
        }
