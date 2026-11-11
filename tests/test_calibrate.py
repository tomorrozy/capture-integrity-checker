from capture_integrity.calibration import load_profile
from experiments import collect
from experiments.calibrate import main, physical_groups


def test_physical_groups_selects_only_physical(harness_data_dir):
    groups = physical_groups(harness_data_dir)
    assert set(groups) == {"phys-c920", "phys-built-in"}
    assert all(len(m) == 21 for m in groups.values())  # 3 trials x 7 probe modes


def test_main_writes_profile(harness_data_dir, tmp_path):
    out = tmp_path / "calibration.json"
    rc = main(["--data", str(harness_data_dir), "--out", str(out)])
    assert rc == 0
    profile = load_profile(out)
    assert profile.sources == ["phys-c920", "phys-built-in"]
    assert profile.physical_apply_mean_ms > 10.0


def test_main_errors_without_physical(tmp_path):
    dev = [{"device_id": "virt-1", "label": "virtual", "platform": "synthetic",
            "l1_suspicion": "0.6", "l1_status": "ok", "driver": "dshow",
            "card": "OBS Virtual Camera", "notes": ""}]
    collect._write_csv(tmp_path / "devices.csv", collect.DEV_FIELDS, dev)
    collect._write_csv(tmp_path / "measurements.csv", collect.MEAS_FIELDS, [])
    out = tmp_path / "p.json"
    rc = main(["--data", str(tmp_path), "--out", str(out)])
    assert rc == 1
    assert not out.exists()