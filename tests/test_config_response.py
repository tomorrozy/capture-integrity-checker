import pytest

from capture_integrity.config_response import (
    ConfigResponseLayer,
    extract_features,
    score_features,
)
from capture_integrity.types import ProbeStatus


def test_virtual_features_score_high(virtual_measurements):
    feats = extract_features(virtual_measurements)
    assert feats["mean_apply_ms"] < 3.0
    assert feats["odd_accept_ratio"] == 1.0
    assert score_features(feats) > 0.6


def test_physical_features_score_low(physical_measurements):
    feats = extract_features(physical_measurements)
    assert feats["mean_apply_ms"] > 10.0
    assert feats["odd_accept_ratio"] == 0.0
    assert score_features(feats) < 0.2


def test_clamp_and_reject_ratios(physical_measurements):
    feats = extract_features(physical_measurements)
    assert feats["clamp_ratio"] == pytest.approx(2 / 5)
    assert feats["reject_ratio"] == pytest.approx(1 / 5)


def test_layer_with_mock_backend(virtual_measurements, make_mock_backend):
    backend = make_mock_backend(virtual_measurements)
    modes = tuple(m.requested for m in virtual_measurements)
    result = ConfigResponseLayer().run("mock", backend=backend, modes=modes)
    assert result.status == ProbeStatus.OK
    assert result.suspicion > 0.6
    assert "features" in result.evidence
    assert backend.closed is False  # injected backend is not owned by the layer


def test_layer_unavailable_when_backend_fails():
    # No opencv-python installed here => OpenCVBackend import fails => unavailable.
    result = ConfigResponseLayer().run("nonexistent-device-999")
    assert result.status == ProbeStatus.UNAVAILABLE