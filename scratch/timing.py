"""Scratch: time each mode on a single persistent DSHOW handle. Usage: timing.py [index]"""
import sys
import time

import cv2

from capture_integrity.config_response import DEFAULT_PROBE_MODES

idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
print(f"opened idx={idx}", cap.isOpened(), flush=True)
if cap.isOpened():
    for mode in DEFAULT_PROBE_MODES:
        t0 = time.perf_counter()
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, mode.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, mode.height)
        cap.set(cv2.CAP_PROP_FPS, mode.fps)
        apply_ms = (time.perf_counter() - t0) * 1000.0
        eff = f"{int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}"
        t1 = time.perf_counter()
        ok, frame = cap.read()
        read_ms = (time.perf_counter() - t1) * 1000.0
        print(f"req={mode.width}x{mode.height}@{mode.fps}: apply={apply_ms:.1f} read={read_ms:.1f} ok={ok} eff={eff}", flush=True)
    cap.release()
