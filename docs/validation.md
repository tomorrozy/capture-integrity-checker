# Validation Report

Mode: `real` · trials/device: 10 · decision threshold: 0.5 · target APCER: 0.1

> **Scope (limited — read first).** This is a **real-hardware** result, but a narrow
> one: Windows + DirectShow, **1 physical** (integrated camera) vs **1 virtual** (OBS
> Virtual Camera), **L2 only** (L1 descriptor is Linux-only in v0.1, hence
> `unavailable` here), 10 trials/device. It is **not** the ≥2-physical / ≥2-virtual
> ablation and **not** ISO/IEC 30107-3.
>
> **Finding.** Odd-mode acceptance separates the two: the physical driver clamps odd
> requests (1234×567→1280×720, 999×999→960×540) while OBS accepts them **exactly**
> (1234×567, 999×999) → mean L2 **0.400 (OBS)** vs **0.000 (physical)**. The timing
> feature does not help on this backend: DirectShow graph renegotiation dominates
> `apply_ms` for both (physical ≈1248 ms, OBS ≈465 ms), so the timing term is 0 on
> both. The virtual cam therefore scores 0.400 — below the default 0.5 threshold, so
> the `Ablation @0.5` row shows TPR 0 — but a **calibrated 0.400** threshold gives
> APCER 0.000 / BPCER 0.000. Treat 0.5 as a placeholder; calibrate per deployment.

## Device matrix

| Device | Label | Platform | L1 status | Driver | Card |
|---|---|---|---|---|---|
| phys-integrated | physical | windows | unavailable |  |  |
| virt-obs | virtual | windows | unavailable |  |  |

## Per-device mean suspicion

| Device | Label | mean L1 | mean L2 | mean fused |
|---|---|---|---|---|
| phys-integrated | physical | n/a | 0.000 | 0.000 |
| virt-obs | virtual | n/a | 0.400 | 0.400 |

## Ablation @ threshold 0.5

| Config | n pos | n neg | Detection rate (TPR) | FPR |
|---|---|---|---|---|
| L1 only | 0 | 0 | 0.000 | 0.000 |
| L2 only | 10 | 10 | 0.000 | 0.000 |
| L1+L2 | 10 | 10 | 0.000 | 0.000 |

## BPCER @ APCER=0.1

| Config | Threshold | Achieved APCER | BPCER |
|---|---|---|---|
| L1 only | n/a | n/a | n/a |
| L2 only | 0.400 | 0.000 | 0.000 |
| L1+L2 | 0.400 | 0.000 | 0.000 |

## Method

- Decision rule: suspicion >= threshold => detected as virtual.
- APCER = fraction of attack (virtual/adversarial) samples not detected; BPCER = fraction of physical samples wrongly detected.
- BPCER@APCER: threshold set at the target-APCER quantile of positive scores; BPCER measured on negatives at that threshold.
- L2 scored relative to a calibration profile (physical sources: phys-integrated; apply mean=1247.69ms).

## Caveats

- Small-sample, non-lab-grade (not ISO/IEC 30107-3). Numbers scoped to these devices.
- The adversarial device models descriptor spoofing (Windows FriendlyName / recompiled module): L1 is expected to fail there; L2 should retain separation.
- No claim of APCER 1e-3 or of ending injection attacks.
