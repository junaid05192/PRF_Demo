"""
Camera service — captures a frame every 5 minutes and uploads it to the API.

Uses picamera2 to capture JPEG stills from the Raspberry Pi Camera Module
(CSI, e.g. imx708), stamps a CCTV-style date/time overlay on each frame,
and posts it to the API.
"""
import io
import time
from datetime import datetime

import requests
from PIL import Image, ImageDraw, ImageFont
from picamera2 import Picamera2

from common import API_URL, NODE_ID

POST_INTERVAL_SECONDS = 300
FRAME_SIZE = (640, 480)

_picam2 = None
_font = None


def _get_camera():
    global _picam2
    if _picam2 is None:
        _picam2 = Picamera2()
        config = _picam2.create_still_configuration(main={"size": FRAME_SIZE})
        _picam2.configure(config)
        _picam2.start()
        time.sleep(2)  # let auto-exposure/white-balance settle
    return _picam2


def _get_font():
    global _font
    if _font is None:
        try:
            _font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 16
            )
        except OSError:
            _font = ImageFont.load_default()
    return _font


def _stamp_timestamp(image: Image.Image) -> None:
    """Draw a CCTV-style timestamp in the bottom-right corner, in place."""
    text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    draw = ImageDraw.Draw(image)
    font = _get_font()
    margin = 8
    x0, y0, x1, y1 = draw.textbbox((0, 0), text, font=font)
    x = image.width - (x1 - x0) - margin
    y = image.height - (y1 - y0) - margin
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx or dy:
                draw.text((x + dx, y + dy), text, font=font, fill="black")
    draw.text((x, y), text, font=font, fill="white")


def capture_frame() -> bytes:
    """Capture one frame, stamp it with the current date/time, and return JPEG bytes."""
    camera = _get_camera()
    raw = io.BytesIO()
    camera.capture_file(raw, format="jpeg")
    raw.seek(0)
    image = Image.open(raw).convert("RGB")
    _stamp_timestamp(image)
    buf = io.BytesIO()
    image.save(buf, format="jpeg", quality=90)
    return buf.getvalue()


def main():
    print(f"[camera_service] node={NODE_ID} -> {API_URL}")
    while True:
        frame = capture_frame()
        try:
            resp = requests.post(
                f"{API_URL}/api/camera/frame",
                data={"node_id": NODE_ID},
                files={"file": ("frame.jpg", frame, "image/jpeg")},
                timeout=10,
            )
            resp.raise_for_status()
            print(f"[camera_service] posted frame ({len(frame)} bytes)")
        except requests.RequestException as exc:
            print(f"[camera_service] failed to post: {exc}")
        time.sleep(POST_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
