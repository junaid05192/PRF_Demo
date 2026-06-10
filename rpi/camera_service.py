"""
Camera service — captures a frame every 5 seconds and uploads it to the API.

Uses picamera2 to capture JPEG stills from the Raspberry Pi Camera Module
(CSI, e.g. imx708) and posts each frame to the API.
"""
import io
import time

import requests
from picamera2 import Picamera2

from common import API_URL, NODE_ID

POST_INTERVAL_SECONDS = 5
FRAME_SIZE = (640, 480)

_picam2 = None


def _get_camera():
    global _picam2
    if _picam2 is None:
        _picam2 = Picamera2()
        config = _picam2.create_still_configuration(main={"size": FRAME_SIZE})
        _picam2.configure(config)
        _picam2.start()
        time.sleep(2)  # let auto-exposure/white-balance settle
    return _picam2


def capture_frame() -> bytes:
    """Return one JPEG frame as bytes."""
    camera = _get_camera()
    buf = io.BytesIO()
    camera.capture_file(buf, format="jpeg")
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
