"""Collect raw probe measurements into CSV for the validation harness.

Real mode (needs a camera + opencv-python):
  python experiments/collect.py --devices experiments/devices.json --trials 30 --out data

Synthetic mode (no hardware; clearly labeled, for pipeline smoke tests / CI):
  python experiments/collect.py --synthetic --trials 30 --out scratch --seed 1
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

from capture_integrity.config_response import DEFAULT_PROBE_MODES, OpenCVBackend
from capture_integrity.descriptor import DescriptorLayer
from capture_integrity.types import Mode, ProbeMeasurement, ProbeStatus

MEAS_FIELDS = ["device_id", "label", "trial", "req_w", "req_h", "req_fps",
               "eff_w", "eff_h", "eff_fps", "apply_ms", "accepted", "first_frame_ms"]
DEV_FIELDS = ["device_id", "label", "platform", "l1_suspicion", "l1_status",
              "driver", "card", "notes"]

# Synthetic device matrix. The adversarial device models descriptor spoofing
# (Windows FriendlyName / recompiled module): L1 looks physical, L2 stays virtual.
SYNTHETIC_DEVICES = [
    {"id": "phys-c920", "label": "physical", "l1": 0.05, "driver": "uvcvideo", "card": "HD Pro Webcam C920"},
    {"id": "phys-built-in", "label": "physical", "l1": 0.05, "driver": "uvcvideo", "card": "Integrated Camera"},
    {"id": "virt-obs", "label": "virtual", "l1": 0.6, "driver": "dshow", "card": "OBS Virtual Camera"},
    {"id": "virt-loopback", "label": "virtual", "l1": 0.95, "driver": "v4l2 loopback", "card": "Loopback"},
    {"id": "adv-spoofed", "label": "adversarial", "l1": 0.05, "driver": "uvcvideo",
     "card": "HD Pro Webcam C920", "notes": "spoofed descriptor; virtual config-response"},
]


def _write_csv(path: Path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def _meas_row(device_id, label, trial, m: ProbeMeasurement):
    eff = m.effective
    return {
        "device_id": device_id, "label": label, "trial": trial,
        "req_w": m.requested.width, "req_h": m.requested.height, "req_fps": m.requested.fps,
        "eff_w": eff.width if eff else "", "eff_h": eff.height if eff else "",
        "eff_fps": eff.fps if eff else "",
        "apply_ms": round(m.apply_ms, 4), "accepted": int(m.accepted),
        "first_frame_ms": round(m.first_frame_ms, 4) if m.first_frame_ms is not None else "",
    }


def collect_real(devices, trials, modes):
    dev_rows, meas_rows = [], []
    for dev in devices:
        l1 = DescriptorLayer().run(dev["device"])
        cap = l1.evidence.get("capability", {})
        dev_rows.append({
            "device_id": dev["id"], "label": dev["label"], "platform": dev.get("platform", ""),
            "l1_suspicion": l1.suspicion if l1.status == ProbeStatus.OK else "",
            "l1_status": l1.status.value, "driver": cap.get("driver", ""),
            "card": cap.get("card", ""), "notes": dev.get("notes", ""),
        })
        backend = OpenCVBackend(dev["device"])
        skipped = 0
        try:
            for trial in range(trials):
                for mode in modes:
                    try:
                        m = backend.reconfigure(mode)
                    except Exception:  # a flaky mode must not abort the device's collection
                        skipped += 1
                        continue
                    meas_rows.append(_meas_row(dev["id"], dev["label"], trial, m))
        finally:
            backend.close()
        print(f"collected {dev['id']} ({dev['label']}): {trials} trials, "
              f"{skipped} skipped, L1={l1.status.value}")
    return dev_rows, meas_rows


def _synthetic_meas(label, modes, rng):
    out = []
    for mode in modes:
        if label == "physical":
            apply = max(1.0, rng.gauss(45, 12))
            eff = mode if mode.is_standard() else Mode(1280, 720, 30.0)  # clamp odd modes
            first = max(1.0, rng.gauss(30, 8))
        else:  # virtual / adversarial: fast, consistent, accepts odd modes exactly
            apply = max(0.05, rng.gauss(0.6, 0.15))
            eff = mode
            first = max(0.2, rng.gauss(2.0, 0.5))
        out.append(ProbeMeasurement(mode, eff, apply, True, first))
    return out


def collect_synthetic(trials, modes, seed):
    rng = random.Random(seed)
    dev_rows, meas_rows = [], []
    for dev in SYNTHETIC_DEVICES:
        dev_rows.append({
            "device_id": dev["id"], "label": dev["label"], "platform": "synthetic",
            "l1_suspicion": dev["l1"], "l1_status": "ok",
            "driver": dev["driver"], "card": dev["card"], "notes": dev.get("notes", "synthetic"),
        })
        for trial in range(trials):
            for m in _synthetic_meas(dev["label"], modes, rng):
                meas_rows.append(_meas_row(dev["id"], dev["label"], trial, m))
    return dev_rows, meas_rows


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Collect validation probe data")
    p.add_argument("--devices", default="experiments/devices.json")
    p.add_argument("--trials", type=int, default=30)
    p.add_argument("--out", default="data")
    p.add_argument("--synthetic", action="store_true")
    p.add_argument("--seed", type=int, default=1)
    args = p.parse_args(argv)

    modes = DEFAULT_PROBE_MODES
    if args.synthetic:
        dev_rows, meas_rows = collect_synthetic(args.trials, modes, args.seed)
        mode = "synthetic"
    else:
        devices = json.loads(Path(args.devices).read_text(encoding="utf-8"))
        dev_rows, meas_rows = collect_real(devices, args.trials, modes)
        mode = "real"

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    _write_csv(out / "devices.csv", DEV_FIELDS, dev_rows)
    _write_csv(out / "measurements.csv", MEAS_FIELDS, meas_rows)
    meta = {
        "mode": mode, "trials": args.trials,
        "seed": args.seed if args.synthetic else None,
        "probe_modes": [[m.width, m.height, m.fps] for m in modes],
        "devices": [d["device_id"] for d in dev_rows],
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"wrote {len(dev_rows)} devices, {len(meas_rows)} measurements to {out}/ (mode={mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())