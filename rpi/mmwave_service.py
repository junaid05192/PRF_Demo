"""
mmWave service — Pen-level metrics from the IWR6843AOP.

On startup, sends profile.cfg to the sensor over its config UART
(/dev/serial0, 115200 baud) to start streaming, then reads TLV point-cloud
frames from the data UART (/dev/ttyAMA1, falling back to /dev/ttyAMA4) at
921600 baud. Each post interval, the points collected over a short read
window are reduced to pen-level metrics: bird_count, activity_score,
clustering_score, and a spatial heatmap.
"""
import os
import struct
import time

import requests
import serial

from common import API_URL, NODE_ID

POST_INTERVAL_SECONDS = 10
READ_WINDOW_SECONDS = 1.0
GRID_SIZE = 4  # 4x4 spatial heatmap of the pen floor

CONFIG_PORT = "/dev/serial0"
DATA_PORT = "/dev/ttyAMA1" if os.path.exists("/dev/ttyAMA1") else "/dev/ttyAMA4"
CONFIG_BAUD = 115200
DATA_BAUD = 921600

MAGIC = bytes([2, 1, 4, 3, 6, 5, 8, 7])
PROFILE_CFG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profile.cfg")

# Sensor floor coverage in meters, used to bin points into the heatmap grid.
# x: lateral span [-X_RANGE, X_RANGE], y: longitudinal span [0, Y_RANGE].
# Tune these to the physical mounting once calibrated.
X_RANGE = float(os.environ.get("MMWAVE_X_RANGE", "2.0"))
Y_RANGE = float(os.environ.get("MMWAVE_Y_RANGE", "4.0"))

_ser = None
_buf = bytearray()


def _load_profile_cmds():
    if not os.path.exists(PROFILE_CFG):
        return []
    with open(PROFILE_CFG) as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("%")]


def _read_until_prompt(cfg_port, timeout=4.0):
    buf = b""
    deadline = time.time() + timeout
    while time.time() < deadline:
        chunk = cfg_port.read(cfg_port.in_waiting or 1)
        if chunk:
            buf += chunk
            if b"mmwDemo:/>" in buf:
                break
        else:
            time.sleep(0.01)
    return buf.decode(errors="ignore").strip()


def configure_sensor():
    """Send profile.cfg over the config UART to start the sensor streaming."""
    cmds = _load_profile_cmds()
    if not cmds:
        print("[mmwave_service] no profile.cfg found, assuming sensor already running")
        return
    try:
        with serial.Serial(CONFIG_PORT, CONFIG_BAUD, timeout=1) as cfg:
            for reset_cmd in ("sensorStop", "flushCfg"):
                cfg.write((reset_cmd + "\n").encode())
                time.sleep(0.5)
                cfg.read(cfg.in_waiting or 1)
            time.sleep(0.3)
            for cmd in cmds:
                cfg.write((cmd + "\n").encode())
                resp = _read_until_prompt(cfg)
                print(f"[mmwave_service][cfg] {cmd} -> {resp[:80]}")
    except Exception as exc:
        print(f"[mmwave_service] failed to configure sensor: {exc}")


def _parse_frame(buf, total_len):
    """Parse one TLV frame body, return list of points with x, y, z, v, snr."""
    _, _, _, _, _, _, _num_obj, num_tlvs, _ = struct.unpack_from("<8sIIIIIIII", buf, 0)

    points = []
    side_snr = []
    offset = 40
    for _ in range(num_tlvs):
        if offset + 8 > total_len:
            break
        tlv_type, tlv_len = struct.unpack_from("<II", buf, offset)
        offset += 8
        if tlv_type == 1:  # detected points: x, y, z, velocity (float32 each)
            n = tlv_len // 16
            for i in range(n):
                x, y, z, v = struct.unpack_from("<ffff", buf, offset + i * 16)
                points.append({"x": x, "y": y, "z": z, "v": v})
        elif tlv_type == 7:  # side info: snr, noise (int16 each, units 0.1 dB)
            n = tlv_len // 4
            for i in range(n):
                snr, _noise = struct.unpack_from("<hh", buf, offset + i * 4)
                side_snr.append(snr * 0.1)
        offset += tlv_len

    for i, pt in enumerate(points):
        pt["snr"] = side_snr[i] if i < len(side_snr) else 0.0
    return points


def _get_serial():
    global _ser
    if _ser is None:
        _ser = serial.Serial(DATA_PORT, DATA_BAUD, timeout=0.05)
    return _ser


def _read_frames(duration):
    """Read the data UART for `duration` seconds, return a list of point-clouds."""
    ser = _get_serial()
    frames = []
    deadline = time.time() + duration
    while time.time() < deadline:
        raw = ser.read(4096)
        if raw:
            _buf.extend(raw)

        while len(_buf) >= 40:
            idx = _buf.find(MAGIC)
            if idx < 0:
                _buf.clear()
                break
            if idx > 0:
                del _buf[:idx]
            if len(_buf) < 40:
                break

            _, _, total_len = struct.unpack_from("<8sII", _buf, 0)
            if total_len < 40 or total_len > 32768:
                del _buf[:8]  # spurious magic match, skip past it
                continue
            if len(_buf) < total_len:
                break

            frame_bytes = bytes(_buf[:total_len])
            del _buf[:total_len]
            frames.append(_parse_frame(frame_bytes, total_len))
    return frames


def _build_heatmap(points):
    grid = [[0.0] * GRID_SIZE for _ in range(GRID_SIZE)]
    if not points:
        return grid

    for pt in points:
        col = int((pt["x"] + X_RANGE) / (2 * X_RANGE) * GRID_SIZE)
        row = int(pt["y"] / Y_RANGE * GRID_SIZE)
        col = max(0, min(GRID_SIZE - 1, col))
        row = max(0, min(GRID_SIZE - 1, row))
        grid[row][col] += 1

    max_count = max(max(row) for row in grid)
    if max_count > 0:
        grid = [[round(c / max_count, 2) for c in row] for row in grid]
    return grid


def _clustering_score(grid):
    """Herfindahl-style concentration index, normalized to 0 (uniform) - 1 (one cell)."""
    cells = [c for row in grid for c in row]
    total = sum(cells)
    if total == 0:
        return 0.0
    shares = [c / total for c in cells]
    h = sum(s * s for s in shares)
    n = len(cells)
    return round(max(0.0, (h - 1 / n) / (1 - 1 / n)), 2)


def read_mmwave_frame():
    """Read recent point-cloud frames and reduce them to pen-level metrics."""
    frames = _read_frames(READ_WINDOW_SECONDS)
    points = frames[-1] if frames else []

    v_vals = [abs(p["v"]) for p in points]
    v_mean = sum(v_vals) / len(v_vals) if v_vals else 0.0

    heatmap = _build_heatmap(points)

    return {
        "node_id": NODE_ID,
        "bird_count": len(points),
        "activity_score": round(min(100.0, v_mean * 150), 1),
        "clustering_score": _clustering_score(heatmap),
        "heatmap": heatmap,
    }


def main():
    print(f"[mmwave_service] node={NODE_ID} -> {API_URL}")
    print(f"[mmwave_service] config={CONFIG_PORT}@{CONFIG_BAUD} data={DATA_PORT}@{DATA_BAUD}")
    configure_sensor()

    while True:
        try:
            reading = read_mmwave_frame()
        except Exception as exc:
            print(f"[mmwave_service] sensor read failed: {exc}")
            global _ser
            if _ser is not None:
                try:
                    _ser.close()
                except Exception:
                    pass
                _ser = None
            time.sleep(POST_INTERVAL_SECONDS)
            continue

        try:
            resp = requests.post(f"{API_URL}/api/readings/mmwave", json=reading, timeout=5)
            resp.raise_for_status()
            print(f"[mmwave_service] posted bird_count={reading['bird_count']} "
                  f"activity={reading['activity_score']} clustering={reading['clustering_score']}")
        except requests.RequestException as exc:
            print(f"[mmwave_service] failed to post: {exc}")

        time.sleep(max(0, POST_INTERVAL_SECONDS - READ_WINDOW_SECONDS))


if __name__ == "__main__":
    main()
