"""Shared CSV parsing for the validation harness. Pure: stdlib + core types only."""
from __future__ import annotations

import csv
from pathlib import Path

from capture_integrity.types import Mode, ProbeMeasurement


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_measurement(row: dict) -> ProbeMeasurement:
    eff = None
    if row["eff_w"]:
        eff = Mode(int(row["eff_w"]), int(row["eff_h"]), float(row["eff_fps"]))
    first = float(row["first_frame_ms"]) if row["first_frame_ms"] else None
    return ProbeMeasurement(
        Mode(int(row["req_w"]), int(row["req_h"]), float(row["req_fps"])),
        eff, float(row["apply_ms"]), bool(int(row["accepted"])), first,
    )