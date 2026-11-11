# CaptureIntegrityChecker

> **改一个设备名称就能绕过现有虚拟摄像头检测，而这个开源模块让这件事不再免费。**

A pluggable capture-path integrity layer that flags virtual cameras which survive
device-name spoofing — a continuous **`0.0–1.0` trust signal** you run *before*
face liveness. Defense-in-depth, not a hard block.

[![CI](https://github.com/tomorrozy/capture-integrity-checker/actions/workflows/ci.yml/badge.svg)](https://github.com/tomorrozy/capture-integrity-checker/actions/workflows/ci.yml)
![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)
<!-- TODO: add PyPI badge once published -->

> **Status: v0.1.0 in development.** The L1/L2 module and the validation harness
> (collect / calibrate / ablation) are implemented with a tested, zero-dependency
> core — 38 hardware-free tests, CI green on ubuntu/windows × Python 3.10–3.13.
> A first **real-hardware** run (Windows/DSHOW, limited scope) is in
> [docs/validation.md](docs/validation.md); the full ≥2/≥2 matrix is pending — see the
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

## Install

Python ≥ 3.10. The core has **zero runtime dependencies**; probing a live camera
needs OpenCV (optional).

```bash
pip install -e ".[dev]"      # core + test tooling
pip install -e ".[opencv]"   # + OpenCV, needed to probe a real device session
```

From source only for now — a PyPI release is on the [roadmap](#roadmap).

## 2-minute quickstart

```bash
python -m capture_integrity.demo --device 0   # prints score + status + raw evidence
# after editing install: capture-integrity-demo --device 0
```

Example output on a host where neither layer can probe (here: Windows without
OpenCV). It degrades to a **neutral `0.5`** with `status: "unavailable"` rather than
falsely reporting "trusted":

```json
{
  "score": 0.5,
  "signals": {},
  "status": "unavailable",
  "evidence": {
    "descriptor": {"status": "unavailable", "reason": "platform 'win32' not supported in v0.1"},
    "config_response": {"status": "unavailable", "error": "No module named 'cv2'"}
  }
}
```

On Linux with a real camera you get a genuine score; on Windows/macOS the descriptor
layer stays `unavailable` (see [Three-layer signal](#three-layer-signal)).

## Interface

```python
from capture_integrity import CaptureIntegrityChecker

checker = CaptureIntegrityChecker(
    layers=("descriptor", "config_response"),  # "forensics" is planned, not scored in v0.1
    probe_budget_ms=1500,
)
result = checker.integrity_score(device="/dev/video0")  # Windows/Linux: int index or path

result.score      # 0..1, higher = more trustworthy
result.signals    # per-layer trust (1 - suspicion), e.g. {"descriptor": 0.9, "config_response": 0.86}
result.status     # "ok" | "partial" | "unavailable" | "error"
result.evidence   # raw per-layer measurements + reason/error, fully auditable
```

**Failure semantics:** if **no** layer can produce a reading, `score == 0.5` and
`status == "unavailable"` (unknown ⇒ uncertain, never silently trusted). If only
some layers are available, their weights are renormalized and `status == "partial"`.
Probes run in the pre-session idle window and are cached per device fingerprint.
**L1 reads device metadata only. L2 reconfigures the device and briefly reads one
frame per mode purely to time first-frame latency, then discards it — no frame
content is stored or transmitted.**

## Three-layer signal

| Layer | Signal | Weight | v0.1 |
|---|---|---|---|
| L1 descriptor | `VIDIOC_QUERYCAP.driver` / `card` (**Linux only**) | 0.2 | on (Linux) |
| L2 config-response | reconfig apply-time distribution, silent-truncation boundary, odd-mode acceptance | 0.7 | on |
| L3 forensics (planned) | frame jitter, buffer timestamps, double-JPEG | 0.1 | not scored |

`score = 1 − Σ wᵢ·suspicionᵢ`, renormalized over the layers that returned a
reading. Rule/statistical baseline by default — **zero training dependency**; an ML
backend is interface-only. Every score ships with raw `evidence` for audit.

## Integration

Additive and reversible — land the module first, wire it in later. It runs after the
existing label check and before the Liveness Fallback, contributing a *soft* signal:

```python
# examples/minimal_integration.py
def combine(existing_trust: float, integrity_score: float, weight: float = 0.3) -> float:
    return (1 - weight) * existing_trust + weight * integrity_score
```

`combine` is a one-line example helper, not a package export — substitute your own
fusion. `UNAVAILABLE` stays neutral (`0.5`), so an unknown device never drags the
trust score down, and the module is never a hard block.

## Validation

Target protocol: ablation across ≥2 physical cameras, ≥2 virtual-camera
implementations, and spoofed-label adversarial variants (TPR / FPR, BPCER @
APCER=1e-1).

**First real-hardware run (limited scope).** Windows + DirectShow, 1 physical
(integrated camera) vs 1 virtual (OBS Virtual Camera), **L2 only** (L1 is Linux-only
in v0.1), 10 trials each. Odd-mode acceptance separates them — the physical driver
clamps odd requests, OBS accepts them exactly → **mean L2 0.400 (virtual) vs 0.000
(physical)**. Timing does not help on this backend (DirectShow renegotiation dominates
`apply_ms`), so the fused score sits at 0.400 — below the default 0.5 threshold — but a
**calibrated 0.400** threshold gives **APCER 0.000 / BPCER 0.000**. Full report:
[docs/validation.md](docs/validation.md); raw CSV: [`data/`](data/).

> Small-sample (10 trials/device), non-lab-grade (**not** ISO/IEC 30107-3), and **not**
> the ≥2/≥2 matrix — that needs a Linux host with ≥2 physical cameras + v4l2loopback
> ([runbook](docs/collecting.md)). Treat 0.5 as a placeholder decision threshold and
> calibrate per deployment.

## Honest boundaries

- **False positives:** fast physical drivers / capture cards may trip L2 →
  calibration profile, tunable thresholds, soft signal; FPR is published.
- **Bypass still possible:** recompiled kernel module, injected artificial delay.
  This is a baseline, not a complete fix.
- **Not a liveness detector:** it scores the *capture path*, not the face. Keep it
  in front of liveness — it does not replace it.
- **Out of scope (v0.1):** Windows/macOS descriptor probing, hardware HDMI-capture
  injection, macOS CoreMediaIO.

## Roadmap

- [x] L1 descriptor + L2 config-response probes + `calibrate.py`
- [x] Validation harness: collect / calibrate / ablation (`experiments/`)
- [x] First real-hardware run (Windows/DSHOW, L2-only, 1 physical + OBS) → [docs/validation.md](docs/validation.md)
- [ ] Full ≥2 physical / ≥2 virtual matrix + adversarial variant — needs a Linux host ([runbook](docs/collecting.md))
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

[Apache-2.0](LICENSE) — chosen over MIT for its explicit **patent grant**, which
matters when the module is folded into commercial biometric stacks. Swap to MIT if
you prefer maximum permissiveness.
