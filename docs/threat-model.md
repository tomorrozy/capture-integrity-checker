# Threat Model

This document states what CaptureIntegrityChecker protects, against whom, and
where its guarantees stop. It is deliberately conservative: the module is a
**defense-in-depth baseline**, not a complete anti-injection solution.

## 1. Scope: what this module is (and isn't)

CaptureIntegrityChecker checks **capture-path authenticity** — whether the video
device feeding a face liveness / biometric pipeline is a trustworthy physical
camera or a software virtual camera injecting a stream. It runs *before* liveness
detection and emits a soft `0.0–1.0` integrity score.

It is **not**:
- A liveness / presentation-attack detector (that is the downstream model's job).
- A deepfake or replayed-content detector. A deepfake shown to a *real* camera is a
  presentation attack (out of scope here); a stream injected through a *virtual*
  camera is in scope as a capture-path problem.
- A hard block. The score is a soft signal folded into an existing trust score.
- A guarantee. It raises attacker cost; it does not end injection attacks.

## 2. Assets & security objective

- **Asset:** the integrity of the capture path — the assumption that frames
  originate from a physical sensor observing the real scene.
- **Objective:** make software stream injection detectably more expensive than a
  trivial device-name change, and surface a calibrated, auditable signal that
  integrators can weight in their trust decision.
- **Security property:** detect spoofed virtual cameras with low false positives
  on common physical cameras, and degrade gracefully (signal uncertainty) when
  probing is not possible.

## 3. System context & trust boundaries

```
real scene → physical sensor ┊ driver/OS → capture API → [this module] → liveness → trust decision
                             ┊
                    trust boundary ── software to the right of the sensor can
                    fabricate a "camera" (virtual-camera stream injection)
```

The key boundary is between the **physical sensor** and the **software capture
stack**. A virtual camera lives entirely in software below the capture API and can
present arbitrary frames. The module trusts that the OS/driver stack reports device
metadata with some fidelity; if the kernel itself is compromised, no userspace
detector can be trusted (see Assumptions).

## 4. Adversary model (capability tiers)

| Tier | Capability | Example | In scope? |
|---|---|---|---|
| T0 trivial | Run a virtual camera with default labels | OBS Virtual Camera, stock v4l2loopback | ✅ primary target |
| T1 low | Spoof device labels | `card_label="HD Pro Webcam C920"`; edit DirectShow `FriendlyName` | ✅ primary target |
| T2 medium | Forge timing/format behavior to mimic physical negotiation | inject artificial reconfig delay, fake a mode list | ⚠️ partial — raises cost, arms race |
| T3 high | Control the driver/kernel stack | recompile v4l2loopback to erase the `driver` string | ❌ expected to bypass; documented |
| T4 hardware | Malicious hardware in the physical signal chain | HDMI capture card fed an injected signal | ❌ out of scope |

## 5. Attack vectors & mitigations

| Vector | Layer | Mitigation | Residual |
|---|---|---|---|
| Default-label virtual camera | L1 | driver string / DevicePath / CLSID prior | T1 spoofs labels → L1 alone insufficient |
| Label-spoofed virtual camera | L2 | reconfig apply-time distribution, silent-truncation boundary, odd-mode acceptance | T2 can forge timing → arms race |
| Replay / deepfake stream via virtual cam | L1+L2 | detect the virtual capture path (content-agnostic) | does not inspect frame content |
| Frame-level injection artifacts | L3 (optional, off) | arrival jitter, buffer timestamps, double-JPEG | not a v0.1 dependency |

L1 is a low-weight prior (0.2); L2 is the core signal (0.7). The design bet: a T1
attacker who spoofs labels still leaves config-response metadata that differs from
physical negotiation. L2 must be calibrated against a physical-camera profile to
keep false positives low.

## 6. Assumptions

- The host OS and kernel are not fully compromised. A kernel-level adversary (T3)
  can fabricate any metadata; userspace detection cannot win.
- The module can open the device and probe in a pre-session idle window (or observe
  the host's own reconfigurations in passive mode).
- Device metadata (`VIDIOC_QUERYCAP`, DirectShow properties) is readable with the
  integrator's process privileges.
- Physical-camera calibration profiles are representative of the deployment's
  camera population.

## 7. Failure modes & default behavior

- **Probe unavailable** (device busy, permission denied, unsupported platform):
  return a neutral/uncertain score with `evidence.probe_status="unavailable"`.
  **Do not silently treat as trusted.** Integrators must choose fail-open vs
  fail-closed policy for the unknown case explicitly.
- **Partial signals** (one layer errors): score from available layers and flag the
  missing layer in `evidence`; widen uncertainty rather than over-trust.
- **Calibration drift** (unseen physical camera model): may raise false positives;
  mitigated by tunable thresholds and published FPR; integrators can recalibrate.

## 8. Residual risk & known limitations

- T2/T3 attackers can bypass; this is an arms race, not a solved problem.
- Small-sample validation; not ISO/IEC 30107-3 lab-grade. Numbers are scoped to the
  tested devices (see `docs/validation.md`).
- False positives on fast physical drivers / capture cards are possible.
- The score is only as good as the integrator's trust fusion; a soft signal ignored
  downstream provides no protection.

## 9. Out of scope (v0.1)

- Hardware HDMI / capture-card injection (T4): the capture path is physically real;
  injection happens upstream of the sensor boundary this module observes.
- macOS / CoreMediaIO cameras.
- Presentation attacks on real cameras (print / replay / mask / deepfake-to-screen)
  — handled by liveness detection, not this module.
- Network-level attacks on the video transport after capture.

## 10. Validation stance

Claims are backed by an open ablation (L1-only / L2-only / L1+L2) across ≥2 physical
cameras, ≥2 virtual-camera implementations, and spoofed-label adversarial variants,
reporting detection rate / FPR and BPCER @ APCER=1e-1. Raw CSV + scripts are
published. The core claim under test: on label-spoofed adversarial samples, L2
retains discriminative power where L1 fails. **No claim** of APCER 1e-3 or of ending
injection attacks is made.