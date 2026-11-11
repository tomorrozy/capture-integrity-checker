"""Run the harness CLIs the way users do (python experiments/x.py) to catch
script-mode import regressions that package-mode unit tests miss."""
import subprocess
import sys
from pathlib import Path

from capture_integrity.calibration import load_profile

REPO = Path(__file__).resolve().parent.parent


def _run(script, *args):
    return subprocess.run(
        [sys.executable, str(REPO / "experiments" / script), *args],
        cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def test_calibrate_script_mode(harness_data_dir, tmp_path):
    out = tmp_path / "calibration.json"
    r = _run("calibrate.py", "--data", str(harness_data_dir), "--out", str(out))
    assert r.returncode == 0, r.stderr
    assert load_profile(out).sources == ["phys-c920", "phys-built-in"]


def test_run_validation_script_mode_with_profile(harness_data_dir, tmp_path):
    prof = tmp_path / "calibration.json"
    assert _run("calibrate.py", "--data", str(harness_data_dir), "--out", str(prof)).returncode == 0
    out = tmp_path / "validation.md"
    r = _run("run_validation.py", "--data", str(harness_data_dir),
             "--profile", str(prof), "--out", str(out))
    assert r.returncode == 0, r.stderr
    text = out.read_text(encoding="utf-8")
    assert "SYNTHETIC" in text
    assert "calibration profile" in text
    assert (tmp_path / "scores.csv").exists()