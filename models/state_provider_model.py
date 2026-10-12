from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class StateProviderModel:
    provider_id: str
    display_name: str
    provider_type: str
    status: str
    description: str
    created_at: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateProviderModel":
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "display_name": self.display_name,
            "provider_type": self.provider_type,
            "status": self.status,
            "description": self.description,
            "created_at": self.created_at,
        }
