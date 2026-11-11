"""Run with: python -m capture_integrity.demo --device 0"""
from __future__ import annotations

import argparse
import json

from .checker import CaptureIntegrityChecker


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CaptureIntegrityChecker demo")
    parser.add_argument("--device", default="0", help="camera index, /dev/videoN, or DevicePath")
    parser.add_argument("--layers", default="descriptor,config_response")
    args = parser.parse_args(argv)

    device = int(args.device) if args.device.isdigit() else args.device
    checker = CaptureIntegrityChecker(layers=tuple(args.layers.split(",")))
    result = checker.integrity_score(device)

    print(json.dumps(
        {
            "score": result.score,
            "signals": result.signals,
            "status": result.status.value,
            "evidence": result.evidence,
        },
        indent=2,
        default=lambda o: getattr(o, "__dict__", str(o)),
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())