# Validation Harness

Reproducible collection + ablation analysis for CaptureIntegrityChecker.

## Files

- `metrics.py` — pure ablation metrics (unit-tested in `tests/test_metrics.py`)
- `collect.py` — probe devices, write raw CSV (real or synthetic)
- `run_validation.py` — recompute the ablation from CSV → markdown report
- `devices.example.json` — device manifest template

## Protocol

1. **Device matrix**: ≥2 physical cameras (negative), ≥2 virtual implementations
   (positive: OBS Virtual Camera, v4l2loopback + FFmpeg), ≥1 adversarial (spoofed
   descriptor). Copy `devices.example.json` → `devices.json` and set device
   indices / paths. Labels: `physical` | `virtual` | `adversarial`.
2. **Collect** ≥30 trials/device (needs camera + OpenCV):
   ```bash
   pip install -e ".[opencv]"
   python experiments/collect.py --devices experiments/devices.json --trials 30 --out data
   ```
3. **Analyze** (no hardware):
   ```bash
   python experiments/run_validation.py --data data --out docs/validation.md
   ```
4. Commit `data/` (raw CSV) + `docs/validation.md` for reproducibility.

## Outputs

- `data/devices.csv`, `data/measurements.csv`, `data/meta.json` — raw, auditable
- `docs/validation.md` — ablation @ threshold + BPCER@APCER=0.1 + per-device means
- `docs/scores.csv` — per-trial L1 / L2 / fused scores

## Synthetic mode (no hardware)

```bash
python experiments/collect.py --synthetic --trials 30 --out scratch --seed 1
python experiments/run_validation.py --data scratch --out scratch/validation.synthetic.md
```

Clearly labeled **SYNTHETIC**; for pipeline smoke tests / CI only. Never publish
synthetic numbers as real-device results. Keep synthetic outputs in `scratch/`
(gitignored).

## Metrics

- Decision rule: `suspicion >= threshold` ⇒ detected as virtual.
- APCER = fraction of attack (virtual/adversarial) samples not detected.
- BPCER = fraction of physical samples wrongly detected.
- BPCER@APCER=0.1: threshold at the 10th-percentile of positive scores; BPCER
  measured on negatives at that threshold.

## Honest scope

Small-sample, non-lab-grade (not ISO/IEC 30107-3). L2 uses default rule thresholds
(calibrate per deployment for real use). The adversarial device demonstrates the
core claim: L1 fails on spoofed descriptors, L2 retains separation.