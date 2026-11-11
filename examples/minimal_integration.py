"""Minimal integration: after the label check, before Liveness Fallback (soft signal)."""
from capture_integrity import CaptureIntegrityChecker


def combine(existing_trust: float, integrity_score: float, weight: float = 0.3) -> float:
    return (1 - weight) * existing_trust + weight * integrity_score


def assess(device, existing_trust: float) -> float:
    checker = CaptureIntegrityChecker()
    integrity = checker.integrity_score(device)
    # Soft signal only — never a hard block. Unknown (UNAVAILABLE) stays neutral (0.5).
    return combine(existing_trust, integrity.score)


if __name__ == "__main__":
    print(assess(0, existing_trust=0.9))