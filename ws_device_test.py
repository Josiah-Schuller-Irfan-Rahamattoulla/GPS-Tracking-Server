import asyncio
import json

import websockets


DEVICE_ID = 67
DEVICE_TOKEN = "sim_device_12345_123456789"

WS_URL = f"ws://127.0.0.1:8000/v1/ws/devices/{DEVICE_ID}?token={DEVICE_TOKEN}"


async def main() -> None:
    print(f"Connecting to {WS_URL} ...", flush=True)
    async with websockets.connect(WS_URL) as ws:
        print("WebSocket connected. Waiting for messages...", flush=True)
        while True:
            msg = await ws.recv()
            try:
                data = json.loads(msg)
            except Exception:
                data = msg
            print("WS message:", data, flush=True)


if __name__ == "__main__":
    asyncio.run(main())

