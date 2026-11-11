"""Scratch diagnostic: probe each DEFAULT mode on device 0 in isolation."""
import time

import cv2

from capture_integrity.config_response import DEFAULT_PROBE_MODES

for mode in DEFAULT_PROBE_MODES:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print(f"{mode.width}x{mode.height}@{mode.fps}: OPEN FAIL")
        continue
    try:
        t0 = time.perf_counter()
        ok_w = cap.set(cv2.CAP_PROP_FRAME_WIDTH, mode.width)
        ok_h = cap.set(cv2.CAP_PROP_FRAME_HEIGHT, mode.height)
        cap.set(cv2.CAP_PROP_FPS, mode.fps)
        apply_ms = (time.perf_counter() - t0) * 1000.0
        ew = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        eh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        t1 = time.perf_counter()
        ok_frame, _ = cap.read()
        first = (time.perf_counter() - t1) * 1000.0 if ok_frame else None
        print(
            f"{mode.width}x{mode.height}@{mode.fps}: apply={apply_ms:.2f}ms "
            f"eff={ew}x{eh} set_ok={bool(ok_w and ok_h)} frame_ok={ok_frame} first={first}"
        )
    except Exception as exc:  # noqa: BLE001 - diagnostic
        print(f"{mode.width}x{mode.height}@{mode.fps}: EXC {type(exc).__name__}: {str(exc)[:90]}")
    finally:
        cap.release()
