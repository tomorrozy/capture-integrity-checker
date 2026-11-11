"""Pure ablation metrics. No hardware, no I/O — fully unit-testable.

Decision rule: a sample is "detected as virtual" when suspicion >= threshold.
  APCER = fraction of attack (virtual/adversarial) samples NOT detected.
  BPCER = fraction of bona fide (physical) samples wrongly detected.
"""
from __future__ import annotations

# Must match capture_integrity.checker.CaptureIntegrityChecker.WEIGHTS.
W_DESCRIPTOR = 0.2
W_CONFIG_RESPONSE = 0.7


def fuse_suspicion(l1: float, l2: float) -> float:
    return (W_DESCRIPTOR * l1 + W_CONFIG_RESPONSE * l2) / (W_DESCRIPTOR + W_CONFIG_RESPONSE)


def detection_rates(positive_scores, negative_scores, threshold: float) -> tuple[float, float]:
    pos = list(positive_scores)
    neg = list(negative_scores)
    tpr = sum(s >= threshold for s in pos) / len(pos) if pos else 0.0
    fpr = sum(s >= threshold for s in neg) / len(neg) if neg else 0.0
    return tpr, fpr


def bpcer_at_apcer(positive_scores, negative_scores, target_apcer: float = 0.1) -> dict | None:
    """Pick the threshold at the target_apcer quantile of positive scores, then
    report the achieved APCER and the BPCER on negatives at that threshold."""
    pos = sorted(positive_scores)
    neg = list(negative_scores)
    if not pos:
        return None
    idx = min(len(pos) - 1, int(target_apcer * len(pos)))
    threshold = pos[idx]
    apcer = sum(s < threshold for s in pos) / len(pos)
    bpcer = sum(s >= threshold for s in neg) / len(neg) if neg else 0.0
    return {"threshold": threshold, "apcer": apcer, "bpcer": bpcer}