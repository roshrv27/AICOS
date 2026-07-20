from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SourceTrustPolicy:
    _weights: dict[str, float] = field(default_factory=lambda: {
        "OFFICIAL_DOCUMENTATION": 1.00,
        "OFFICIAL_GITHUB": 0.95,
        "RESEARCH": 0.90,
        "CONFERENCE": 0.85,
        "VENDOR_BLOGS": 0.80,
        "YOUTUBE": 0.70,
        "COMMUNITY": 0.60,
        "REDDIT": 0.50,
        "X": 0.40,
    })

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        if weights is not None:
            for key, value in weights.items():
                self.validate_weight(value)
            self._weights = dict(weights)
        else:
            self._weights = {
                "OFFICIAL_DOCUMENTATION": 1.00,
                "OFFICIAL_GITHUB": 0.95,
                "RESEARCH": 0.90,
                "CONFERENCE": 0.85,
                "VENDOR_BLOGS": 0.80,
                "YOUTUBE": 0.70,
                "COMMUNITY": 0.60,
                "REDDIT": 0.50,
                "X": 0.40,
            }

    @staticmethod
    def validate_weight(value: float) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError(
                f"Trust weight must be between 0.0 and 1.0, got {value}"
            )

    def get_weight(self, source_type: str) -> float:
        return self._weights.get(source_type, 0.5)

    def set_weight(self, source_type: str, weight: float) -> None:
        self.validate_weight(weight)
        self._weights[source_type] = weight

    @property
    def weights(self) -> dict[str, float]:
        return dict(self._weights)

    def to_dict(self) -> dict[str, float]:
        return dict(self._weights)

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> SourceTrustPolicy:
        return cls(weights=data)
