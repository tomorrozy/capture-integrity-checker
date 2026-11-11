# CaptureIntegrityChecker

> **改一个设备名称就能绕过现有虚拟摄像头检测，而这个开源模块让这件事不再免费。**

A pluggable capture-path integrity layer for face liveness / biometric systems. It
runs **before** liveness detection and emits a continuous `0.0–1.0` trust signal
that flags virtual cameras which survive device-name spoofing — using
configuration-response metadata, not label matching alone.

[![CI](https://github.com/tomorrozy/capture-integrity-checker/actions/workflows/ci.yml/badge.svg)](https://github.com/tomorrozy/capture-integrity-checker/actions/workflows/ci.yml)
![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)
<!-- TODO: add PyPI badge once published -->

> **Status: v0.1.0 in development.** The L1/L2 module and the validation harness
> (collect / calibrate / ablation) are implemented with a tested, zero-dependency
> core — 32 hardware-free tests, CI green on ubuntu/windows × Python 3.10–3.13.
> Real-device data collection is pending; see the
> [collection runbook](docs/collecting.md) and [Roadmap](#roadmap).

---

## The problem

Most open-source virtual-camera detection matches driver labels / device names
(`OBS Virtual Camera`, `ManyCam`, …). An attacker can spoof `v4l2loopback`'s
`card_label` or a DirectShow filter's `FriendlyName` to impersonate a physical
camera and bypass that check at near-zero cost. Closed SDKs ship stream-injection
detection, but the open ecosystem lacks a reproducible, auditable,
training-free baseline.

**Positioning:** defense-in-depth, not a silver bullet. This module does **not**
replace liveness detection, does **not** hard-block, and does **not** claim to end
injection attacks. It raises the cost of a trivial bypass and outputs a *soft*
signal you can fold into an existing trust score.

## Demo

<!-- TODO: add assets/demo.gif — split-screen: renamed virtual cam bypasses label
     check (left) vs. this module still scores it low (right) -->
_Demo GIF coming with v0.1.0._

## Quickstart

From source (PyPI release pending):

```bash
pip install -e ".[dev]"
python -m capture_integrity.demo --device 0   # prints score + raw evidence
```

```python
from capture_integrity import CaptureIntegrityChecker

checker = CaptureIntegrityChecker(
    layers=("descriptor", "config_response"),  # "forensics" optional, off by default
    probe_budget_ms=1500,
)
result = checker.integrity_score(device="/dev/video0")  # Windows: index / DevicePath
result.score      # 0.87 — higher is more trustworthy
result.signals    # {"descriptor": 0.9, "config_response": 0.86}
result.evidence   # raw measurements, auditable
```

Probes run in the pre-session idle window and are cached per device fingerprint.
**L1/L2 read device metadata only — no frame content is read or stored.**

## Three-layer design

| Layer | Signal | Weight | Default |
|---|---|---|---|
| L1 descriptor | `VIDIOC_QUERYCAP.driver` (Linux) / DevicePath + FilterData (Win) | 0.2 | on |
| L2 config-response | reconfig apply-time distribution, silent-truncation boundary, odd-mode acceptance | 0.7 | on |
| L3 forensics (optional) | frame jitter, buffer timestamps, double-JPEG | 0.1 | off |

`score = 1 − Σ wᵢ·suspicionᵢ`. Rule/statistical baseline by default — **zero
training dependency**; an ML backend is interface-only. Every score ships with raw
`evidence` for audit.

## Minimal integration

```python
# after the existing label check, before Liveness Fallback
integrity = checker.integrity_score(device)
trust_score = combine(existing_trust, integrity.score, weight=0.3)  # soft signal
```

Additive and reversible: land the module first, wire it in later (3 lines).

## Validation

Ablation across ≥2 physical cameras, ≥2 virtual-camera implementations, and
spoofed-label adversarial variants. Reports detection rate / FPR for L1-only,
L2-only, L1+L2, and BPCER @ APCER=1e-1 with each layer's marginal contribution.

> Small-sample, non-lab-grade (not ISO/IEC 30107-3). Numbers are scoped to the
> tested devices; raw CSV + scripts are published for reproduction. The real
> `docs/validation.md` is generated from your own cameras — follow the
> [real-device collection runbook](docs/collecting.md).

## Honest boundaries

- **False positives:** fast physical drivers / capture cards may trip L2 →
  calibration profile, tunable thresholds, soft signal; FPR is published.
- **Bypass still possible:** recompiled kernel module, injected artificial delay.
  This is a baseline, not a complete fix.
- **Out of scope (v0.1):** hardware HDMI-capture injection, macOS (CoreMediaIO).

## Roadmap

- [x] L1 descriptor + L2 config-response probes + `calibrate.py`
- [x] Validation harness: collect / calibrate / ablation (`experiments/`)
- [ ] Real device matrix + ablation report (`docs/validation.md`) — needs hardware ([runbook](docs/collecting.md))
- [ ] Demo GIF + 2-minute quickstart verified end-to-end
- [ ] v0.1.0 release + upstream PR (module-only, no core changes)
- [ ] Optional L3 forensics; macOS support (later)

## Contributing

PRs welcome. This repo ships a default
[PR template](.github/PULL_REQUEST_TEMPLATE.md) — keep changes additive and
include reproducible evidence. See [SECURITY.md](SECURITY.md) for private
vulnerability reporting.

## Suggested repository topics

`virtual-camera` · `camera-spoofing` · `face-anti-spoofing` · `liveness-detection`
· `biometric-security` · `v4l2` · `directshow` · `defense-in-depth` ·
`security-tools` · `python`

## License

[Apache-2.0](LICENSE).