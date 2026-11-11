"""Build a physical-camera calibration profile from collected CSV. No hardware needed.

  python experiments/calibrate.py --data data --out calibration.json

Selects devices labeled ``physical``, groups their probe measurements across all
trials, and writes a CalibrationProfile JSON. That profile is consumed by
``run_validation.py --profile`` (profile-relative L2 scoring) and by the checker
at deployment time. Only known-physical cameras may be used as calibration sources.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

if not __package__:  # running as a script: make the repo root importable
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from capture_integrity.calibration import build_profile, save_profile
from experiments._data import read_csv, to_measurement


def physical_groups(data_dir: Path) -> dict[str, list]:
    """Measurements grouped by device_id, restricted to label == 'physical'."""
    devices = {r["device_id"]: r for r in read_csv(data_dir / "devices.csv")}
    groups: dict[str, list] = defaultdict(list)
    for row in read_csv(data_dir / "measurements.csv"):
        dev = devices.get(row["device_id"])
        if dev is None or dev["label"] != "physical":
            continue
        groups[row["device_id"]].append(to_measurement(row))
    return dict(groups)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Build a physical-camera calibration profile from CSV")
    p.add_argument("--data", default="data", help="collect.py output dir (devices.csv + measurements.csv)")
    p.add_argument("--out", default="calibration.json", help="profile JSON to write")
    args = p.parse_args(argv)

    groups = physical_groups(Path(args.data))
    if not groups:
        print("error: no devices labeled 'physical' in --data; cannot calibrate. "
              "Calibration sources must be known-physical cameras.")
        return 1
    empty = [d for d, m in groups.items() if not m]
    if empty:
        print(f"error: physical devices with no measurements: {', '.join(empty)}")
        return 1

    profile = build_profile(groups)
    save_profile(profile, args.out)
    print(f"calibration profile from {len(profile.sources)} physical device(s): {', '.join(profile.sources)}")
    print(f"  apply mean={profile.physical_apply_mean_ms:.3f}ms "
          f"std={profile.physical_apply_std_ms:.3f}ms "
          f"odd_accept={profile.physical_odd_accept_ratio:.3f}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())