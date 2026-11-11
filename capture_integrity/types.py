"""Core data model for capture-path integrity scoring."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProbeStatus(str, Enum):
    OK = "ok"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


# Resolutions treated as standard camera modes; anything else is an odd-mode probe.
_STANDARD_RESOLUTIONS = frozenset({
    (320, 240), (640, 480), (800, 600), (1024, 768),
    (1280, 720), (1920, 1080), (2560, 1440), (3840, 2160),
})


@dataclass(frozen=True)
class Mode:
    width: int
    height: int
    fps: float = 30.0

    def is_standard(self) -> bool:
        return (self.width, self.height) in _STANDARD_RESOLUTIONS


@dataclass
class ProbeMeasurement:
    requested: Mode
    effective: Mode | None
    apply_ms: float
    accepted: bool
    first_frame_ms: float | None = None


@dataclass
class LayerResult:
    name: str
    suspicion: float            # 0..1, higher => more likely virtual
    status: ProbeStatus
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class IntegrityResult:
    score: float                # 0..1, higher => more trustworthy
    signals: dict[str, float]   # per-layer trust (1 - suspicion)
    status: ProbeStatus
    evidence: dict[str, Any] = field(default_factory=dict)