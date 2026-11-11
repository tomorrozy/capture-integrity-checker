"""Scratch: find which OpenCV index/backend opens a readable camera. No frames saved."""
import cv2

print("opencv", cv2.__version__)
for idx in range(4):
    for name, api in (("DSHOW", cv2.CAP_DSHOW), ("MSMF", cv2.CAP_MSMF)):
        cap = cv2.VideoCapture(idx, api)
        opened = cap.isOpened()
        ok, w, h = False, 0, 0
        try:
            if opened:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                ok, frame = cap.read()
                if ok and frame is not None:
                    h, w = frame.shape[:2]
        except Exception as exc:  # noqa: BLE001 - diagnostic
            print(f"idx={idx} {name}: EXC {type(exc).__name__}: {str(exc)[:60]}")
            cap.release()
            continue
        print(f"idx={idx} {name}: opened={opened} read_ok={ok} size={w}x{h}")
        cap.release()
