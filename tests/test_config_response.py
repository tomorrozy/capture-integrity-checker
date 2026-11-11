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


def _fake_cv2(monkeypatch, opens_api):
    import sys
    import types

    calls = []

    class FakeCap:
        def __init__(self, ok):
            self._ok = ok

        def isOpened(self):
            return self._ok

        def release(self):
            pass

    def video_capture(index, api=None):
        calls.append(api)
        return FakeCap(api == opens_api)

    fake = types.SimpleNamespace(CAP_DSHOW=700, CAP_MSMF=1400, VideoCapture=video_capture)
    monkeypatch.setitem(sys.modules, "cv2", fake)
    monkeypatch.setattr(sys, "platform", "win32")
    return calls


def test_windows_backend_prefers_dshow(monkeypatch):
    calls = _fake_cv2(monkeypatch, opens_api=700)
    from capture_integrity.config_response import OpenCVBackend

    OpenCVBackend(1)
    assert calls == [700]  # DirectShow opens first, so MSMF is never tried


def test_windows_backend_falls_back_to_msmf(monkeypatch):
    calls = _fake_cv2(monkeypatch, opens_api=1400)
    from capture_integrity.config_response import OpenCVBackend

    OpenCVBackend(1)
    assert calls == [700, 1400]


def test_odd_accept_ignores_fps_float_noise():
    requested = Mode(1234, 567, 15)
    effective = Mode(1234, 567, 15.000015)  # driver-reported fps noise
    feats = extract_features([ProbeMeasurement(requested, effective, 0.5, True, 1.0)])
    assert feats["odd_accept_ratio"] == 1.0


def test_reconfigure_keeps_acceptance_when_frame_decode_fails(monkeypatch):
    import sys
    import types

    class Cap:
        def __init__(self):
            self.props = {}

        def set(self, prop, val):
            self.props[prop] = val
            return True

        def get(self, prop):
            return self.props.get(prop, 0)

        def read(self):
            raise RuntimeError("decode failure on odd frame")

        def isOpened(self):
            return True

        def release(self):
            pass

    fake = types.SimpleNamespace(
        CAP_DSHOW=700, CAP_MSMF=1400,
        CAP_PROP_FRAME_WIDTH=3, CAP_PROP_FRAME_HEIGHT=4, CAP_PROP_FPS=5,
        VideoCapture=lambda idx, api=None: Cap(),
    )
    monkeypatch.setitem(sys.modules, "cv2", fake)
    monkeypatch.setattr(sys, "platform", "linux")  # simple default-open branch

    from capture_integrity.config_response import OpenCVBackend

    m = OpenCVBackend(1).reconfigure(Mode(1234, 567, 15))
    assert m.accepted is True
    assert m.effective == Mode(1234, 567, 15)  # odd mode accepted exactly
    assert m.first_frame_ms is None