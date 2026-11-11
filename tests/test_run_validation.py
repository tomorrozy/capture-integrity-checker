from capture_integrity.calibration import build_profile
from experiments.calibrate import physical_groups
from experiments.run_validation import ablation, build_scores, render_report


def _mean_l2(records, label):
    vals = [r["l2"] for r in records if r["label"] == label]
    return sum(vals) / len(vals)


def test_ablation_l2_beats_l1_on_spoofed(harness_data_dir):
    records, _ = build_scores(harness_data_dir)
    abl = ablation(records, 0.5, 0.1)
    assert set(abl) == {"L1 only", "L2 only", "L1+L2"}
    # L1 misses the spoofed-label adversarial device; L2 retains separation.
    assert abl["L2 only"]["tpr"] > abl["L1 only"]["tpr"]
    assert abl["L2 only"]["fpr"] == 0.0


def test_profile_raises_virtual_suspicion(harness_data_dir):
    base, _ = build_scores(harness_data_dir)
    profile = build_profile(physical_groups(harness_data_dir))
    prof, _ = build_scores(harness_data_dir, profile)
    assert _mean_l2(prof, "virtual") > _mean_l2(base, "virtual")
    assert _mean_l2(prof, "physical") < 0.05


def test_render_report_notes_profile_and_synthetic(harness_data_dir):
    records, devices = build_scores(harness_data_dir)
    abl = ablation(records, 0.5, 0.1)
    profile = build_profile(physical_groups(harness_data_dir))
    meta = {"mode": "synthetic", "trials": 3}
    report = render_report(records, devices, abl, meta, 0.5, 0.1, profile)
    assert "SYNTHETIC" in report
    assert "calibration profile" in report
    assert "phys-c920" in report