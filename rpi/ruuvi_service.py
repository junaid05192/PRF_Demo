"""
Ruuvi Tag service — temperature/humidity from the BLE sensor near the litter.

Currently generates dummy data shaped like real Ruuvi readings.
Replace `read_ruuvi_tag()` with `ruuvitag_sensor.RuuviTagSensor` once the
physical tag and its MAC address are available.
"""
import random
import time

import requests

from common import API_URL, NODE_ID

POST_INTERVAL_SECONDS = 30

_state = {
    "temperature": 29.0,
    "humidity": 65.0,
}


def read_ruuvi_tag():
    """Return one simulated Ruuvi reading. Replace with real BLE scan."""
    _state["temperature"] = max(20, min(35, _state["temperature"] + random.uniform(-0.3, 0.3)))
    _state["humidity"] = max(40, min(85, _state["humidity"] + random.uniform(-1, 1)))

    return {
        "node_id": NODE_ID,
        "temperature": round(_state["temperature"], 1),
        "humidity": round(_state["humidity"], 1),
    }


def main():
    print(f"[ruuvi_service] node={NODE_ID} -> {API_URL}")
    while True:
        reading = read_ruuvi_tag()
        try:
            resp = requests.post(f"{API_URL}/api/readings/environment", json=reading, timeout=5)
            resp.raise_for_status()
            print(f"[ruuvi_service] posted {reading}")
        except requests.RequestException as exc:
            print(f"[ruuvi_service] failed to post: {exc}")
        time.sleep(POST_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
