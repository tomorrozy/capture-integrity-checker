# Real-device collection runbook

How to produce a **real** `docs/validation.md` and a calibration profile from actual
cameras. The synthetic mode (`collect.py --synthetic`) is a CI / pipeline smoke test
only — **never publish synthetic numbers as real-device results.**

> You run the collection on hardware you control; the analysis is pure and
> reproducible from the CSV. If you send back `data/` + `calibration.json`, the
> report can be regenerated without your cameras.

---

## 0. Prerequisites

- Python ≥ 3.10, this repo cloned.
- Install with the OpenCV extra (real capture) and dev extra (tests):
  ```bash
  pip install -e ".[opencv,dev]"
  ```
- Cameras you control. **Linux is recommended for the full matrix** (v4l2loopback +
  a spoofable descriptor). Windows gives a partial matrix (see §1).

## 1. Platform reality — what v0.1 can actually measure

| | Linux | Windows |
|---|---|---|
| L1 descriptor (`VIDIOC_QUERYCAP.driver`) | **available** | **unavailable** in v0.1 |
| L2 config-response (OpenCV) | available | available |
| Virtual camera | v4l2loopback + FFmpeg / OBS | OBS Virtual Camera (DirectShow) |
| Spoofable descriptor | `card_label` (but see §7) | filter `FriendlyName` |

On Windows, L1 returns `unavailable`; the report's `L1 only` rows are `n/a` and the
fused score falls back to L2 (weights renormalized). This is expected, not a bug.

## 2. Build the device matrix

Target: **≥2 physical** (negative), **≥2 virtual implementations** (positive),
**≥1 adversarial** (spoofed descriptor). Copy the template and edit:

```bash
cp experiments/devices.example.json experiments/devices.json
```

Labels must be exactly `physical` | `virtual` | `adversarial`. `device` is a capture
index (Windows, e.g. `0`) or a path (Linux, e.g. `"/dev/video0"`).

### Linux (full matrix)

```bash
v4l2-ctl --list-devices                 # find the physical /dev/videoN nodes
# two loopback sinks
sudo modprobe v4l2loopback devices=2 video_nr=10,11 card_label="Virtual A,Virtual B"
# virtual #1: FFmpeg test source into /dev/video10
ffmpeg -re -f lavfi -i testsrc=size=1280x720:rate=30 -pix_fmt yuv420p -f v4l2 /dev/video10
# virtual #2: OBS → Start Virtual Camera (OBS sinks to /dev/video11)
```

Example `devices.json`:
```json
[
  {"id":"phys-c920","label":"physical","device":"/dev/video0","platform":"linux","notes":"Logitech C920"},
  {"id":"phys-built-in","label":"physical","device":"/dev/video2","platform":"linux","notes":"integrated"},
  {"id":"virt-ffmpeg","label":"virtual","device":"/dev/video10","platform":"linux","notes":"FFmpeg testsrc"},
  {"id":"virt-obs","label":"virtual","device":"/dev/video11","platform":"linux","notes":"OBS virtual camera"},
  {"id":"adv-spoofed","label":"adversarial","device":"/dev/video12","platform":"linux","notes":"see §7"}
]
```

### Windows (partial matrix)

Install OBS, enable **Tools → Virtual Camera**. Enumerate capture indices (physical
usually `0`/`1`, OBS Virtual Camera next). L1 will be `unavailable`; that is fine —
L2 still separates physical from virtual. For the adversarial variant, spoof the OBS
filter `FriendlyName` to a physical-looking name (§7).

## 3. Collect (needs the cameras live)

```bash
python experiments/collect.py --devices experiments/devices.json --trials 30 --out data
```

Keep each virtual camera **feeding frames** while collecting. Writes
`data/devices.csv`, `data/measurements.csv`, `data/meta.json` (`mode: "real"`).

## 4. Calibrate — physical cameras only

```bash
python experiments/calibrate.py --data data --out calibration.json
```

Selects devices labeled `physical`, builds a `CalibrationProfile` (apply-time
mean/std, odd-mode acceptance). Errors out if no physical device is present —
calibration sources must be known-physical.

## 5. Analyze → the real report

```bash
python experiments/run_validation.py --data data --profile calibration.json --out docs/validation.md
```

Writes `docs/validation.md` (device matrix, per-device means, ablation @ threshold,
BPCER@APCER=0.1) and `docs/scores.csv` (per-trial L1/L2/fused, auditable). Omit
`--profile` to use the default rule thresholds instead.

## 6. Publish / hand off

Commit the **real** artifacts for reproducibility:
`data/` (raw CSV + meta), `calibration.json`, `docs/validation.md`, `docs/scores.csv`.
Keep synthetic outputs in `scratch/` (gitignored). To hand off for report
regeneration, `data/` + `calibration.json` are sufficient.

## 7. The adversarial sample, honestly

The core claim is that **L2 flags a virtual camera even when its descriptor looks
physical**. Getting a *real* sample that defeats L1 requires care:

- **Linux `card_label` rename (easy):** reload loopback with a physical-looking label:
  ```bash
  sudo modprobe -r v4l2loopback
  sudo modprobe v4l2loopback devices=1 video_nr=12 card_label="HD Pro Webcam C920"
  ffmpeg -re -f lavfi -i testsrc=size=1280x720:rate=30 -pix_fmt yuv420p -f v4l2 /dev/video12
  ```
  This defeats **name-only** detectors (the common open-source approach). It does
  **not** defeat our L1: the kernel `driver` string is hardcoded `"v4l2 loopback"`,
  which L1 reads. So this sample shows *L1 robustness to card rename + L2 redundancy*,
  not L1 failure.
- **True L1-failing sample (advanced, threat tier T3):** recompile v4l2loopback with a
  patched `driver` string, or spoof a Windows DirectShow `FriendlyName`. Only then does
  the descriptor look physical to L1. On Windows, L1 is unavailable in v0.1, so such a
  sample exercises **L2 only**.

The synthetic report's `adv-spoofed` device (L1≈0.05) models this T3 / Windows case.
State clearly in `docs/validation.md` which adversarial setup you actually used; do
not imply a stock `card_label` rename defeated L1.

## 8. Sanity checks before publishing

- `data/meta.json` → `"mode": "real"`.
- `devices.csv` → `l1_status` is `ok` on Linux, `unavailable` on Windows.
- Per-device mean L2: physical ≈ 0, virtual/adversarial high; the gap is the signal.
- No `SYNTHETIC` banner in `docs/validation.md` (that banner only appears for synthetic data).