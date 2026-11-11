"""Regenerate the ablation report from collected CSV. No hardware needed.

  python experiments/run_validation.py --data data --out docs/validation.md
  python experiments/run_validation.py --data data --profile calibration.json --out docs/validation.md

Reads devices.csv + measurements.csv (+ meta.json), recomputes per-trial L1/L2/fused
suspicion, and writes a markdown report plus a per-trial scores.csv for audit. With
--profile, L2 is scored relative to a physical-camera calibration profile.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

if not __package__:  # running as a script: make the repo root importable
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from capture_integrity.calibration import load_profile
from capture_integrity.config_response import extract_features, score_features
from experiments._data import read_csv, to_measurement
from experiments.metrics import bpcer_at_apcer, detection_rates, fuse_suspicion

POSITIVE = {"virtual", "adversarial"}
NEGATIVE = {"physical"}


def build_scores(data_dir: Path, profile=None):
    devices = {r["device_id"]: r for r in read_csv(data_dir / "devices.csv")}
    groups = defaultdict(list)
    for row in read_csv(data_dir / "measurements.csv"):
        groups[(row["device_id"], int(row["trial"]))].append(to_measurement(row))

    records = []
    for (dev_id, trial), measurements in sorted(groups.items()):
        dev = devices[dev_id]
        l1 = float(dev["l1_suspicion"]) if dev["l1_suspicion"] else None
        l2 = score_features(extract_features(measurements), profile)
        fused = fuse_suspicion(l1, l2) if l1 is not None else l2
        records.append({"device_id": dev_id, "trial": trial, "label": dev["label"],
                        "l1": l1, "l2": l2, "fused": fused})
    return records, devices


def ablation(records, threshold: float, target_apcer: float):
    configs = {"L1 only": "l1", "L2 only": "l2", "L1+L2": "fused"}
    out = {}
    for name, key in configs.items():
        pos = [r[key] for r in records if r["label"] in POSITIVE and r[key] is not None]
        neg = [r[key] for r in records if r["label"] in NEGATIVE and r[key] is not None]
        tpr, fpr = detection_rates(pos, neg, threshold)
        out[name] = {"tpr": tpr, "fpr": fpr, "n_pos": len(pos), "n_neg": len(neg),
                     "bpcer": bpcer_at_apcer(pos, neg, target_apcer)}
    return out


def render_report(records, devices, abl, meta, threshold, target_apcer, profile=None) -> str:
    mode = meta.get("mode", "unknown")
    L = []
    L.append("# Validation Report\n")
    if mode == "synthetic":
        L.append("> **SYNTHETIC DATA — pipeline smoke test only. Not a real-device result.**\n")
    L.append(f"Mode: `{mode}` · trials/device: {meta.get('trials', '?')} · "
             f"decision threshold: {threshold} · target APCER: {target_apcer}\n")

    L.append("## Device matrix\n")
    L.append("| Device | Label | Platform | L1 status | Driver | Card |")
    L.append("|---|---|---|---|---|---|")
    for d in devices.values():
        L.append(f"| {d['device_id']} | {d['label']} | {d['platform']} | {d['l1_status']} | {d['driver']} | {d['card']} |")
    L.append("")

    L.append("## Per-device mean suspicion\n")
    L.append("| Device | Label | mean L1 | mean L2 | mean fused |")
    L.append("|---|---|---|---|---|")
    by_dev = defaultdict(list)
    for r in records:
        by_dev[r["device_id"]].append(r)
    for dev_id, rs in sorted(by_dev.items()):
        l1vals = [r["l1"] for r in rs if r["l1"] is not None]
        ml1 = f"{sum(l1vals) / len(l1vals):.3f}" if l1vals else "n/a"
        ml2 = sum(r["l2"] for r in rs) / len(rs)
        mf = sum(r["fused"] for r in rs) / len(rs)
        L.append(f"| {dev_id} | {rs[0]['label']} | {ml1} | {ml2:.3f} | {mf:.3f} |")
    L.append("")

    L.append(f"## Ablation @ threshold {threshold}\n")
    L.append("| Config | n pos | n neg | Detection rate (TPR) | FPR |")
    L.append("|---|---|---|---|---|")
    for name, a in abl.items():
        L.append(f"| {name} | {a['n_pos']} | {a['n_neg']} | {a['tpr']:.3f} | {a['fpr']:.3f} |")
    L.append("")

    L.append(f"## BPCER @ APCER={target_apcer}\n")
    L.append("| Config | Threshold | Achieved APCER | BPCER |")
    L.append("|---|---|---|---|")
    for name, a in abl.items():
        ba = a["bpcer"]
        if ba:
            L.append(f"| {name} | {ba['threshold']:.3f} | {ba['apcer']:.3f} | {ba['bpcer']:.3f} |")
        else:
            L.append(f"| {name} | n/a | n/a | n/a |")
    L.append("")

    L.append("## Method\n")
    L.append("- Decision rule: suspicion >= threshold => detected as virtual.")
    L.append("- APCER = fraction of attack (virtual/adversarial) samples not detected; "
             "BPCER = fraction of physical samples wrongly detected.")
    L.append("- BPCER@APCER: threshold set at the target-APCER quantile of positive scores; "
             "BPCER measured on negatives at that threshold.")
    if profile is None:
        L.append("- L2 uses the default rule thresholds (no per-deployment calibration profile).")
    else:
        L.append(f"- L2 scored relative to a calibration profile (physical sources: "
                 f"{', '.join(profile.sources)}; apply mean={profile.physical_apply_mean_ms:.2f}ms).")
    L.append("")
    L.append("## Caveats\n")
    L.append("- Small-sample, non-lab-grade (not ISO/IEC 30107-3). Numbers scoped to these devices.")
    L.append("- The adversarial device models descriptor spoofing (Windows FriendlyName / "
             "recompiled module): L1 is expected to fail there; L2 should retain separation.")
    L.append("- No claim of APCER 1e-3 or of ending injection attacks.")
    L.append("")
    return "\n".join(L)


def _write_scores(path: Path, records):
    fields = ["device_id", "trial", "label", "l1", "l2", "fused"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in records:
            w.writerow({k: ("" if r[k] is None else r[k]) for k in fields})


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Regenerate ablation report from CSV")
    p.add_argument("--data", default="data")
    p.add_argument("--out", default="docs/validation.md")
    p.add_argument("--profile", default=None, help="calibration profile JSON for profile-relative L2 scoring")
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--target-apcer", type=float, default=0.1)
    args = p.parse_args(argv)

    data_dir = Path(args.data)
    meta_path = data_dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {"mode": "unknown"}
    profile = load_profile(args.profile) if args.profile else None

    records, devices = build_scores(data_dir, profile)
    abl = ablation(records, args.threshold, args.target_apcer)
    report = render_report(records, devices, abl, meta, args.threshold, args.target_apcer, profile)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    _write_scores(out.parent / "scores.csv", records)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(report)
    print(f"wrote {out} and {out.parent / 'scores.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())