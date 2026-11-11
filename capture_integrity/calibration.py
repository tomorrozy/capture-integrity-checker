"""Physical-camera calibration profile. Rule baseline, zero training dependency."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .config_response import extract_features
from .types import ProbeMeasurement


@dataclass
class CalibrationProfile:
    physical_apply_mean_ms: float
    physical_apply_std_ms: float
    physical_odd_accept_ratio: float
    sources: list[str]
    version: int = 1


def build_profile(measurements_by_device: dict[str, list[ProbeMeasurement]]) -> CalibrationProfile:
    means: list[float] = []
    stds: list[float] = []
    odds: list[float] = []
    sources: list[str] = []
    for label, measurements in measurements_by_device.items():
        feats = extract_features(measurements)
        means.append(feats["mean_apply_ms"])
        stds.append(feats["std_apply_ms"])
        odds.append(feats["odd_accept_ratio"])
        sources.append(label)
    n = len(sources) or 1
    return CalibrationProfile(
        physical_apply_mean_ms=sum(means) / n,
        physical_apply_std_ms=sum(stds) / n,
        physical_odd_accept_ratio=sum(odds) / n,
        sources=sources,
    )


def save_profile(profile: CalibrationProfile, path: str | Path) -> None:
    Path(path).write_text(json.dumps(asdict(profile), indent=2), encoding="utf-8")


def load_profile(path: str | Path) -> CalibrationProfile:
    return CalibrationProfile(**json.loads(Path(path).read_text(encoding="utf-8")))