"""Layer orchestration and soft-score fusion."""
from __future__ import annotations

from typing import Any

from .config_response import ConfigResponseLayer
from .descriptor import DescriptorLayer
from .types import IntegrityResult, LayerResult, ProbeStatus

# Unknown => uncertain, never silently "trusted" (see docs/threat-model.md §7).
NEUTRAL_SCORE = 0.5


class CaptureIntegrityChecker:
    WEIGHTS = {"descriptor": 0.2, "config_response": 0.7}

    def __init__(
        self,
        layers: tuple[str, ...] = ("descriptor", "config_response"),
        probe_budget_ms: float = 1500.0,
        profile: Any = None,
        backend: Any = None,
    ):
        self.layers = tuple(layers)
        self.probe_budget_ms = probe_budget_ms
        self.profile = profile
        self.backend = backend

    def integrity_score(self, device: Any) -> IntegrityResult:
        results: list[LayerResult] = []
        if "descriptor" in self.layers:
            results.append(DescriptorLayer().run(device))
        if "config_response" in self.layers:
            results.append(ConfigResponseLayer().run(
                device, backend=self.backend, profile=self.profile, budget_ms=self.probe_budget_ms,
            ))
        return self._fuse(results)

    def _fuse(self, results: list[LayerResult]) -> IntegrityResult:
        evidence = {
            r.name: {"status": r.status.value, "suspicion": r.suspicion, **r.evidence}
            for r in results
        }
        available = [r for r in results if r.status == ProbeStatus.OK]
        if not available:
            return IntegrityResult(NEUTRAL_SCORE, {}, ProbeStatus.UNAVAILABLE, evidence)

        total_w = sum(self.WEIGHTS.get(r.name, 0.0) for r in available)
        suspicion = sum(self.WEIGHTS.get(r.name, 0.0) * r.suspicion for r in available) / total_w
        signals = {r.name: 1.0 - r.suspicion for r in available}
        status = ProbeStatus.OK if len(available) == len(results) else ProbeStatus.PARTIAL
        return IntegrityResult(1.0 - suspicion, signals, status, evidence)