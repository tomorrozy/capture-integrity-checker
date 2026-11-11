import struct
import sys

import pytest

from capture_integrity.descriptor import (
    _CAP_FMT,
    _CAP_SIZE,
    DescriptorLayer,
    VIDIOC_QUERYCAP,
    descriptor_suspicion,
    parse_v4l2_capability,
)
from capture_integrity.types import ProbeStatus


def _pack(driver=b"uvcvideo", card=b"HD Pro Webcam C920", bus=b"usb-0000:00:14.0-2"):
    return struct.pack(_CAP_FMT, driver, card, bus, 0x00050F00, 0x84200001, 0x04200001, 0, 0, 0)


def test_parse_capability():
    cap = parse_v4l2_capability(_pack())
    assert cap["driver"] == "uvcvideo"
    assert cap["card"] == "HD Pro Webcam C920"
    assert cap["bus_info"] == "usb-0000:00:14.0-2"


def test_querycap_ioctl_number():
    assert _CAP_SIZE == 104
    assert VIDIOC_QUERYCAP == 0x80685600


def test_loopback_driver_high_even_with_spoofed_card():
    cap = parse_v4l2_capability(_pack(driver=b"v4l2 loopback", card=b"HD Pro Webcam C920"))
    assert descriptor_suspicion(cap) >= 0.9


def test_virtual_card_label_medium():
    cap = parse_v4l2_capability(_pack(driver=b"uvcvideo", card=b"OBS Virtual Camera"))
    assert 0.4 <= descriptor_suspicion(cap) <= 0.7


def test_physical_low():
    assert descriptor_suspicion(parse_v4l2_capability(_pack())) < 0.2


@pytest.mark.skipif(sys.platform.startswith("linux"), reason="non-linux stub path")
def test_descriptor_unavailable_on_non_linux():
    result = DescriptorLayer().run("/dev/video0")
    assert result.status == ProbeStatus.UNAVAILABLE