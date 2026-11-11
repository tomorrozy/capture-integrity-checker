"""L1: capability/descriptor prior. Low weight; never decisive on its own."""
from __future__ import annotations

import struct
import sys
from typing import Any

from .types import LayerResult, ProbeStatus

# struct v4l2_capability {
#   __u8 driver[16]; __u8 card[32]; __u8 bus_info[32];
#   __u32 version; __u32 capabilities; __u32 device_caps; __u32 reserved[3]; }
_CAP_FMT = "<16s32s32sIII3I"
_CAP_SIZE = struct.calcsize(_CAP_FMT)  # 104

_IOC_READ = 2


def _ioc(direction: int, typ: int, nr: int, size: int) -> int:
    return (direction << 30) | (size << 16) | (typ << 8) | nr


VIDIOC_QUERYCAP = _ioc(_IOC_READ, ord("V"), 0, _CAP_SIZE)  # 0x80685600

_VIRTUAL_CARD_TOKENS = ("obs", "manycam", "virtual", "splitcam", "xsplit", "snap camera", "e2esoft")


def parse_v4l2_capability(buf: bytes) -> dict[str, Any]:
    driver, card, bus_info, version, capabilities, device_caps, _r0, _r1, _r2 = struct.unpack(_CAP_FMT, buf)

    def _s(b: bytes) -> str:
        return b.split(b"\0", 1)[0].decode("utf-8", "replace")

    return {
        "driver": _s(driver),
        "card": _s(card),
        "bus_info": _s(bus_info),
        "version": version,
        "capabilities": capabilities,
        "device_caps": device_caps,
    }


def query_linux(device: str) -> dict[str, Any]:
    import fcntl

    with open(device, "rb", buffering=0) as fd:
        buf = bytearray(_CAP_SIZE)
        fcntl.ioctl(fd, VIDIOC_QUERYCAP, buf)
    return parse_v4l2_capability(bytes(buf))


def descriptor_suspicion(cap: dict[str, Any]) -> float:
    driver = cap.get("driver", "").lower()
    card = cap.get("card", "").lower()
    if "loopback" in driver:
        return 0.95  # kernel driver string; spoofing requires a recompiled module (T3)
    if any(token in card for token in _VIRTUAL_CARD_TOKENS):
        return 0.6   # label-based; trivially spoofable (T1)
    return 0.05      # physical prior


class DescriptorLayer:
    name = "descriptor"

    def run(self, device: Any) -> LayerResult:
        if not sys.platform.startswith("linux"):
            return LayerResult(
                self.name, 0.0, ProbeStatus.UNAVAILABLE,
                {"reason": f"platform {sys.platform!r} not supported in v0.1"},
            )
        try:
            cap = query_linux(str(device))
        except Exception as exc:  # device busy / permission / not a v4l2 node
            return LayerResult(self.name, 0.0, ProbeStatus.UNAVAILABLE, {"error": str(exc)})
        return LayerResult(self.name, descriptor_suspicion(cap), ProbeStatus.OK, {"capability": cap})