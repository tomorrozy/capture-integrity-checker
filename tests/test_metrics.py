from experiments.metrics import bpcer_at_apcer, detection_rates, fuse_suspicion


def test_detection_rates():
    pos = [0.9, 0.8, 0.7, 0.2]   # 3 of 4 >= 0.5
    neg = [0.1, 0.6, 0.2, 0.3]   # 1 of 4 >= 0.5
    tpr, fpr = detection_rates(pos, neg, 0.5)
    assert tpr == 0.75
    assert fpr == 0.25


def test_detection_rates_empty():
    assert detection_rates([], [], 0.5) == (0.0, 0.0)


def test_bpcer_at_apcer_clean_separation():
    pos = [i / 10 for i in range(1, 11)]   # 0.1 .. 1.0, n=10
    neg = [0.05] * 10
    res = bpcer_at_apcer(pos, neg, target_apcer=0.1)
    assert res["threshold"] == 0.2          # idx = int(0.1*10) = 1
    assert abs(res["apcer"] - 0.1) < 1e-9
    assert res["bpcer"] == 0.0


def test_bpcer_with_false_positives():
    pos = [0.9] * 9 + [0.1]                 # n=10
    neg = [0.95] * 4 + [0.05] * 6           # 4 of 10 above threshold 0.9
    res = bpcer_at_apcer(pos, neg, target_apcer=0.1)
    assert res["threshold"] == 0.9
    assert abs(res["apcer"] - 0.1) < 1e-9
    assert abs(res["bpcer"] - 0.4) < 1e-9


def test_bpcer_empty_positives():
    assert bpcer_at_apcer([], [0.1, 0.2], 0.1) is None


def test_fuse_matches_checker_weights():
    assert abs(fuse_suspicion(0.95, 0.85) - (0.2 * 0.95 + 0.7 * 0.85) / 0.9) < 1e-9