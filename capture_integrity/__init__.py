"""CaptureIntegrityChecker: capture-path integrity baseline for virtual-camera detection."""
from .checker import CaptureIntegrityChecker
from .types import IntegrityResult, LayerResult, Mode, ProbeMeasurement, ProbeStatus

__version__ = "0.1.0.dev0"

__all__ = [
    "CaptureIntegrityChecker",
    "IntegrityResult",
    "LayerResult",
    "Mode",
    "ProbeMeasurement",
    "ProbeStatus",
    "__version__",
]