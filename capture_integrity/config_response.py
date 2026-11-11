"""L2: configuration-response metadata. The core signal of the module."""
from __future__ import annotations

import statistics
import time
from typing import TYPE_CHECKING, Any, Protocol

from .types import LayerResult, Mode, ProbeMeasurement, ProbeStatus

if TYPE_CHECKING:
    from .calibration import CalibrationProfile

DEFAULT_PROBE_MODES = (
    Mode(640, 480, 30), Mode(1280, 720, 30), Mode(1920, 1080, 30),
    Mode(1234, 567, 15), Mode(999, 999, 30), Mode(640, 480, 60), Mode(3840, 2160, 30),
)

# Starting thresholds — MUST be calibrated against physical cameras before deployment.
_FAST_MEAN_MS = 3.0
_FAST_STD_MS = 1.0


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def extract_features(measurements: list[ProbeMeasurement]) -> dict[str, float]:
    accepted = [m for m in measurements if m.accepted and m.effective is not None]
    apply = [m.apply_ms for m in accepted]
    mean_apply = statistics.fmean(apply) if apply else 0.0
    std_apply = statistics.pstdev(apply) if len(apply) > 1 else 0.0

    odd = [m for m in measurements if not m.requested.is_standard()]
    odd_exact = [m for m in odd if m.accepted and m.effective == m.requested]
    odd_accept = len(odd_exact) / len(odd) if odd else 0.0

    clamped = [m for m in accepted if m.effective != m.requested]
    n = len(measurements) or 1
    frames = [m.first_frame_ms for m in accepted if m.first_frame_ms is not None]
    return {
        "mean_apply_ms": mean_apply,
        "std_apply_ms": std_apply,
        "odd_accept_ratio": odd_accept,
        "clamp_ratio": len(clamped) / n,
        "reject_ratio": 1 - len(accepted) / n,
        "first_frame_mean_ms": statistics.fmean(frames) if frames else 0.0,
        "probe_count": float(len(measurements)),
    }


def score_features(features: dict[str, float], profile: "CalibrationProfile | None" = None) -> float:
    fast_mean, fast_std = _FAST_MEAN_MS, _FAST_STD_MS
    if profile is not None:
        fast_mean = max(0.5, profile.physical_apply_mean_ms * 0.25)
        fast_std = max(0.2, profile.physical_apply_std_ms * 0.5)
    fast = _clamp01((fast_mean - features["mean_apply_ms"]) / fast_mean)
    consistent = _clamp01((fast_std - features["std_apply_ms"]) / fast_std)
    timing_susp = fast * consistent
    acceptance_susp = _clamp01(features["odd_accept_ratio"])
    return _clamp01(0.6 * timing_susp + 0.4 * acceptance_susp)


class CaptureBackend(Protocol):
    def reconfigure(self, mode: Mode) -> ProbeMeasurement: ...
    def close(self) -> None: ...


class OpenCVBackend:
    """Real probe backend. Requires opencv-python (optional extra)."""

    def __init__(self, device: Any):
        import cv2  # optional dependency; ImportError => layer unavailable

        self._cv2 = cv2
        index = int(device) if str(device).isdigit() else device
        self._cap = cv2.VideoCapture(index)
        if not self._cap.isOpened():
            raise RuntimeError(f"cannot open capture device {device!r}")

    def reconfigure(self, mode: Mode) -> ProbeMeasurement:
        cv2 = self._cv2
        t0 = time.perf_counter()
        ok_w = self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, mode.width)
        ok_h = self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, mode.height)
        self._cap.set(cv2.CAP_PROP_FPS, mode.fps)
        apply_ms = (time.perf_counter() - t0) * 1000.0

        eff_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        eff_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        eff_fps = self._cap.get(cv2.CAP_PROP_FPS) or mode.fps

        t1 = time.perf_counter()
        ok_frame, _ = self._cap.read()
        first_frame_ms = (time.perf_counter() - t1) * 1000.0 if ok_frame else None

        accepted = bool(ok_w and ok_h)
        effective = Mode(eff_w, eff_h, eff_fps) if accepted else None
        return ProbeMeasurement(mode, effective, apply_ms, accepted, first_frame_ms)

    def close(self) -> None:
        self._cap.release()


class ConfigResponseLayer:
    name = "config_response"

    def run(
        self,
        device: Any,
        backend: CaptureBackend | None = None,
        modes: tuple[Mode, ...] = DEFAULT_PROBE_MODES,
        profile: "CalibrationProfile | None" = None,
        budget_ms: float = 1500.0,
    ) -> LayerResult:
        owns_backend = backend is None
        try:
            if backend is None:
                backend = OpenCVBackend(device)
        except Exception as exc:
            return LayerResult(self.name, 0.0, ProbeStatus.UNAVAILABLE, {"error": str(exc)})

        measurements: list[ProbeMeasurement] = []
        start = time.perf_counter()
        try:
            for mode in modes:
                if (time.perf_counter() - start) * 1000.0 > budget_ms:
                    break
                measurements.append(backend.reconfigure(mode))
        except Exception as exc:
            return LayerResult(
                self.name, 0.0, ProbeStatus.ERROR,
                {"error": str(exc), "partial": [m.__dict__ for m in measurements]},
            )
        finally:
            if owns_backend:
                backend.close()

        if not measurements:
            return LayerResult(self.name, 0.0, ProbeStatus.UNAVAILABLE, {"reason": "no probes completed"})

        features = extract_features(measurements)
        suspicion = score_features(features, profile)
        return LayerResult(
            self.name, suspicion, ProbeStatus.OK,
            {"features": features, "measurements": [m.__dict__ for m in measurements]},
        )