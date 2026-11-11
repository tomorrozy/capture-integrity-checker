from capture_integrity.checker import NEUTRAL_SCORE, CaptureIntegrityChecker
from capture_integrity.types import LayerResult, ProbeStatus


def test_fuse_all_unavailable_is_neutral_not_trusted():
    checker = CaptureIntegrityChecker()
    results = [
        LayerResult("descriptor", 0.0, ProbeStatus.UNAVAILABLE, {}),
        LayerResult("config_response", 0.0, ProbeStatus.UNAVAILABLE, {}),
    ]
    out = checker._fuse(results)
    assert out.score == NEUTRAL_SCORE
    assert out.status == ProbeStatus.UNAVAILABLE
    assert out.signals == {}


def test_fuse_virtual_detected():
    checker = CaptureIntegrityChecker()
    results = [
        LayerResult("descriptor", 0.95, ProbeStatus.OK, {}),
        LayerResult("config_response", 0.85, ProbeStatus.OK, {}),
    ]
    out = checker._fuse(results)
    assert out.score < 0.2
    assert out.status == ProbeStatus.OK


def test_fuse_physical_trusted():
    checker = CaptureIntegrityChecker()
    results = [
        LayerResult("descriptor", 0.05, ProbeStatus.OK, {}),
        LayerResult("config_response", 0.05, ProbeStatus.OK, {}),
    ]
    out = checker._fuse(results)
    assert out.score > 0.9


def test_fuse_partial_renormalizes_over_available():
    checker = CaptureIntegrityChecker()
    results = [
        LayerResult("descriptor", 0.0, ProbeStatus.UNAVAILABLE, {}),
        LayerResult("config_response", 0.85, ProbeStatus.OK, {}),
    ]
    out = checker._fuse(results)
    assert out.status == ProbeStatus.PARTIAL
    assert abs(out.score - 0.15) < 1e-9


def test_integrity_score_with_mock_backend(virtual_measurements, make_mock_backend):
    backend = make_mock_backend(virtual_measurements)
    checker = CaptureIntegrityChecker(layers=("config_response",), backend=backend)
    out = checker.integrity_score("mock")
    assert out.status == ProbeStatus.OK
    assert out.score < 0.4