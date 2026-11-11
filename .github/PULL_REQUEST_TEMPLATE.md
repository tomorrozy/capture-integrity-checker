## Summary

Adds `CaptureIntegrityChecker`, a pluggable capture-path integrity layer that runs
*before* liveness detection and emits a continuous `0.0–1.0` trust signal. It
detects virtual cameras that survive device-name spoofing, using configuration-
response metadata rather than label matching alone.

- Zero training dependency; rule/statistical baseline by default.
- Additive only: no changes to core liveness / trust logic.
- Soft signal, never a hard block.

Closes {{ISSUE_NUMBER}} · Discussion: {{DISCUSSION_LINK}}

## Motivation

Current virtual-camera detection relies on driver labels / device names (e.g.
matching `OBS Virtual Camera`, `ManyCam`). An attacker can spoof `v4l2loopback`'s
`card_label` or a DirectShow filter's `FriendlyName` to impersonate a physical
camera and bypass this check at near-zero cost.

Minimal bypass (defensive PoC, full context in the issue):

```
{{ONE_LINE_BYPASS_EXAMPLE}}
```

This PR adds a stream-layer signal as defense-in-depth. It does **not** claim to
end injection attacks; it raises the cost of a trivial bypass.

## What's added (scope)

New files only:
- `capture_integrity_checker.py` — public API + score fusion
- `virtual_camera_detector.py` — L1 descriptor + L2 config-response probes
- `tests/` — unit tests (mock devices; CI needs no real camera)
- `examples/minimal_integration.py`
- `docs/validation.md` — ablation + raw data

**Not touched:** core liveness pipeline, trust-score logic, existing detector call
sites, dependencies (reuses existing OpenCV; Linux L1 uses stdlib `fcntl`).

## Design

| Layer | Signal | Weight | Default |
|---|---|---|---|
| L1 descriptor | `VIDIOC_QUERYCAP.driver` (Linux) / DevicePath + FilterData (Win) | 0.2 | on |
| L2 config-response | reconfig apply-time distribution, silent-truncation boundary, odd-mode acceptance | 0.7 | on |
| L3 forensics (optional) | frame jitter, buffer timestamps, double-JPEG | 0.1 | off |

`score = 1 − Σ wᵢ·suspicionᵢ`; every score ships with raw `evidence` for audit.
Probes run in the pre-session idle window and are cached per device fingerprint.
L1/L2 read device metadata only — no frame content is read or stored.

## Minimal integration (3 lines, optional)

```python
# after the existing label check, before Liveness Fallback
integrity = checker.integrity_score(device)
trust_score = combine(existing_trust, integrity.score, weight=0.3)  # soft signal
```

## Validation & ablation

Devices: {{PHYSICAL_1}}, {{PHYSICAL_2}} (negative); OBS Virtual Camera,
v4l2loopback + FFmpeg (positive); spoofed-label variants (adversarial).
≥30 trials/device/mode. Full protocol + CSV: `docs/validation.md`.

| Config | Detection rate | FPR | BPCER @ APCER=1e-1 |
|---|---|---|---|
| L1 only | {{L1_DR}} | {{L1_FPR}} | {{L1_BPCER}} |
| L2 only | {{L2_DR}} | {{L2_FPR}} | {{L2_BPCER}} |
| L1 + L2 | {{BOTH_DR}} | {{BOTH_FPR}} | {{BOTH_BPCER}} |

Key claim under test: on spoofed-label adversarial samples, L2 retains
discriminative power where L1 fails ({{ADVERSARIAL_NOTE}}).

> Small-sample, non-lab-grade (not ISO/IEC 30107-3). Numbers are scoped to the
> tested devices; raw data and scripts are included for reproduction.

## Reproduce / test

```bash
{{INSTALL_CMD}}
python -m capture_integrity.demo --device 0
pytest tests/
python experiments/run_validation.py   # regenerate ablation
```

## Merge-friction note

This module can be merged **without** wiring it into the main flow. Integration is
3 lines and fully reversible. Maintainers may land the module first and enable it
later.

## Limitations (honest boundaries)

- Fast physical drivers / capture cards may false-positive → calibration profile,
  tunable thresholds, soft signal; FPR published.
- Bypass still possible (recompiled module, injected artificial delay) — this is a
  baseline, not a complete fix.
- Out of scope: hardware HDMI-capture injection, macOS (CoreMediaIO) in v0.1.

## Checklist

- [ ] Additive only; core logic untouched
- [ ] CI green; tests use mock devices
- [ ] No new heavy dependencies
- [ ] Ablation raw data + scripts included
- [ ] `SECURITY.md` / threat-model documented
- [ ] Linked issue {{ISSUE_NUMBER}}