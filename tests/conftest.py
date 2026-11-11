"""Hardware-free fixtures: synthetic physical/virtual measurements and a mock backend."""
import pytest

from capture_integrity.types import Mode, ProbeMeasurement


def _m(requested, effective, apply_ms, accepted, first_frame_ms=5.0):
    return ProbeMeasurement(requested, effective, apply_ms, accepted, first_frame_ms)


@pytest.fixture
def virtual_measurements():
    # Fast, consistent apply; odd modes accepted exactly (software virtual camera).
    modes = [Mode(640, 480, 30), Mode(1280, 720, 30), Mode(1234, 567, 15),
             Mode(999, 999, 30), Mode(640, 480, 60)]
    return [_m(m, m, 0.5 + 0.05 * i, True) for i, m in enumerate(modes)]


@pytest.fixture
def physical_measurements():
    # Slower, variable apply; odd modes clamped to nearest standard; one rejected.
    data = [
        (Mode(640, 480, 30), Mode(640, 480, 30), 35.0, True),
        (Mode(1280, 720, 30), Mode(1280, 720, 30), 52.0, True),
        (Mode(1234, 567, 15), Mode(1280, 720, 30), 48.0, True),
        (Mode(999, 999, 30), Mode(1024, 768, 30), 61.0, True),
        (Mode(640, 480, 60), None, 30.0, False),
    ]
    return [_m(*d) for d in data]


class MockBackend:
    def __init__(self, measurements):
        self._measurements = list(measurements)
        self._i = 0
        self.closed = False

    def reconfigure(self, mode):
        m = self._measurements[self._i % len(self._measurements)]
        self._i += 1
        return m

    def close(self):
        self.closed = True


@pytest.fixture
def make_mock_backend():
    return MockBackend


@pytest.fixture
def harness_data_dir(tmp_path):
    """A small synthetic collect.py-style CSV dataset for harness tests (tmp_path only)."""
    import json

    from capture_integrity.config_response import DEFAULT_PROBE_MODES
    from experiments import collect

    dev_rows, meas_rows = collect.collect_synthetic(3, DEFAULT_PROBE_MODES, 1)
    collect._write_csv(tmp_path / "devices.csv", collect.DEV_FIELDS, dev_rows)
    collect._write_csv(tmp_path / "measurements.csv", collect.MEAS_FIELDS, meas_rows)
    (tmp_path / "meta.json").write_text(json.dumps({"mode": "synthetic", "trials": 3}), encoding="utf-8")
    return tmp_path