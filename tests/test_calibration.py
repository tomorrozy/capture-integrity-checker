from capture_integrity.calibration import build_profile, load_profile, save_profile
from capture_integrity.config_response import extract_features, score_features


def test_build_and_roundtrip(tmp_path, physical_measurements):
    profile = build_profile({"cam-A": physical_measurements, "cam-B": physical_measurements})
    assert profile.physical_apply_mean_ms > 10.0
    assert profile.sources == ["cam-A", "cam-B"]
    path = tmp_path / "profile.json"
    save_profile(profile, path)
    assert load_profile(path) == profile


def test_profile_relative_scoring_separates_classes(physical_measurements, virtual_measurements):
    profile = build_profile({"cam": physical_measurements})
    phys = score_features(extract_features(physical_measurements), profile)
    virt = score_features(extract_features(virtual_measurements), profile)
    assert virt > phys
    assert virt > 0.6