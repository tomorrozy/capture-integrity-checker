import pytest

from capture_integrity.config_response import (
    ConfigResponseLayer,
    extract_features,
    score_features,
)
from capture_integrity.types import Mode, ProbeMeasurement, ProbeStatus


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
    # Unprobeable device: backend either cannot import opencv or cannot open it.
    result = ConfigResponseLayer().run("nonexistent-device-999")
    assert result.status == ProbeStatus.UNAVAILABLE


def test_one_failing_mode_does_not_abort_probe():
    class FlakyBackend:
        closed = False

        def reconfigure(self, mode):
            if mode.width == 1280:
                raise RuntimeError("simulated backend abort")
            return ProbeMeasurement(mode, mode, 0.5, True, 5.0)

        def close(self):
            self.closed = True

    modes = (Mode(640, 480, 30), Mode(1280, 720, 30), Mode(1920, 1080, 30))
    backend = FlakyBackend()
    result = ConfigResponseLayer().run("dev", backend=backend, modes=modes)

    assert result.status == ProbeStatus.OK
    assert len(result.evidence["measurements"]) == 2
    assert result.evidence["skipped_modes"] == ["1280x720@30"]
    assert backend.closed is False  # injected backend stays owned by the caller


def test_all_modes_failing_is_unavailable():
    class DeadBackend:
        def reconfigure(self, mode):
            raise RuntimeError("boom")

        def close(self):
            pass

    modes = (Mode(640, 480, 30), Mode(1280, 720, 30))
    result = ConfigResponseLayer().run("dev", backend=DeadBackend(), modes=modes)

    assert result.status == ProbeStatus.UNAVAILABLE
    assert result.evidence["skipped_modes"] == ["640x480@30", "1280x720@30"]