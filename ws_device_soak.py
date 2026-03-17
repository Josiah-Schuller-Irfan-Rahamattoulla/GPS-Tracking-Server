import argparse
import asyncio
import json
import os
import sys
import time
from typing import Optional

import websockets


"""
Production WebSocket soak test for a single device.

This is intended to mimic firmware behavior:
- Connect to /v1/ws/devices/{id}?token=...
- Send an initial ping soon after connect.
- When idle, send a ping every ~10 seconds.
- Log all messages and any disconnect / reconnect events.

You can run this for an extended period (e.g. 30–60 minutes) to validate:
- Connection stability through the ALB (idle timeout = 3600s).
- Device-side idle timeout behavior (server closes after ~120s if we stop pinging).
- Delivery of control / geofence / location messages to the device socket.
"""


def build_ws_url(device_id: int, device_token: str) -> str:
    base = os.getenv("SOAK_WS_BASE", "wss://gpstracking.josiahschuller.au")
    base = base.rstrip("/")
    return f"{base}/v1/ws/devices/{device_id}?token={device_token}"


async def soak_once(
    url: str,
    ping_interval: float,
    stop_at: float,
    conn_index: int,
) -> dict:
    stats = {
        "conn_index": conn_index,
        "connected_at": time.time(),
        "disconnected_at": None,
        "messages": 0,
        "pings_sent": 0,
        "pongs_received": 0,
        "last_message_type": None,
        "close_code": None,
        "close_reason": None,
        "exception": None,
    }
    print(f"[{conn_index}] Connecting to {url} ...", flush=True)
    try:
        async with websockets.connect(url, close_timeout=5) as ws:
            print(f"[{conn_index}] Connected.", flush=True)
            last_ping = 0.0

            async def receiver():
                nonlocal stats
                try:
                    async for msg in ws:
                        stats["messages"] += 1
                        try:
                            data = json.loads(msg)
                        except Exception:
                            data = msg
                        if isinstance(data, dict):
                            msg_type = data.get("type") or data.get("event")
                        else:
                            msg_type = type(data).__name__
                        stats["last_message_type"] = msg_type
                        if isinstance(data, dict) and data.get("type") == "pong":
                            stats["pongs_received"] += 1
                        print(f"[{conn_index}] RX: {data}", flush=True)
                except websockets.ConnectionClosed as e:  # type: ignore[attr-defined]
                    stats["close_code"] = getattr(e, "code", None)
                    stats["close_reason"] = getattr(e, "reason", None)
                    print(
                        f"[{conn_index}] ConnectionClosed code={stats['close_code']} reason={stats['close_reason']}",
                        flush=True,
                    )
                except Exception as e:
                    stats["exception"] = repr(e)
                    print(f"[{conn_index}] Receiver exception: {e!r}", flush=True)

            recv_task = asyncio.create_task(receiver())

            try:
                while time.time() < stop_at and not recv_task.done():
                    now = time.time()
                    if now - last_ping >= ping_interval:
                        payload = {"type": "ping", "timestamp": int(now * 1000)}
                        await ws.send(json.dumps(payload))
                        stats["pings_sent"] += 1
                        last_ping = now
                        print(f"[{conn_index}] TX: {payload}", flush=True)
                    await asyncio.sleep(1.0)
            finally:
                if not recv_task.done():
                    recv_task.cancel()
                    try:
                        await recv_task
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        stats["exception"] = repr(e)
                        print(f"[{conn_index}] Receiver finalization exception: {e!r}", flush=True)
    except Exception as e:
        stats["exception"] = repr(e)
        print(f"[{conn_index}] Connect/outer exception: {e!r}", flush=True)
    finally:
        stats["disconnected_at"] = time.time()

    return stats


async def main_async(
    device_id: int,
    device_token: str,
    duration_seconds: float,
    ping_interval: float,
    reconnect_delay: float,
) -> None:
    url = build_ws_url(device_id, device_token)
    print(
        f"Starting WS soak test for device_id={device_id} "
        f"duration={duration_seconds}s ping_interval={ping_interval}s "
        f"url={url}",
        flush=True,
    )

    end_time = time.time() + duration_seconds
    conn_index = 0
    all_stats = []

    while time.time() < end_time:
        conn_index += 1
        conn_stop = min(end_time, time.time() + 3600)  # safety cap per connection
        stats = await soak_once(url, ping_interval, conn_stop, conn_index)
        all_stats.append(stats)

        remaining = end_time - time.time()
        if remaining <= 0:
            break
        print(
            f"[{conn_index}] Disconnected, sleeping {reconnect_delay:.1f}s before reconnect "
            f"(remaining ~{remaining:.1f}s)...",
            flush=True,
        )
        await asyncio.sleep(reconnect_delay)

    print("\n=== WS Soak Summary ===", flush=True)
    total_conn = len(all_stats)
    total_msgs = sum(s["messages"] for s in all_stats)
    total_pings = sum(s["pings_sent"] for s in all_stats)
    total_pongs = sum(s["pongs_received"] for s in all_stats)
    print(f"Connections: {total_conn}", flush=True)
    print(f"Messages:    {total_msgs}", flush=True)
    print(f"Pings sent:  {total_pings}", flush=True)
    print(f"Pongs recv:  {total_pongs}", flush=True)
    for s in all_stats:
        print(
            f"- conn {s['conn_index']}: "
            f"msgs={s['messages']} pings={s['pings_sent']} pongs={s['pongs_received']} "
            f"close_code={s['close_code']} reason={s['close_reason']} exc={s['exception']}",
            flush=True,
        )


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Device WebSocket soak test against production.")
    p.add_argument("--device-id", type=int, default=int(os.getenv("SOAK_DEVICE_ID", "67")))
    p.add_argument(
        "--device-token",
        type=str,
        default=os.getenv("SOAK_DEVICE_TOKEN", "sim_device_12345_123456789"),
        help="Device access token (or set SOAK_DEVICE_TOKEN).",
    )
    p.add_argument("--duration-seconds", type=float, default=300.0, help="Total soak duration.")
    p.add_argument("--ping-interval", type=float, default=10.0, help="Seconds between pings.")
    p.add_argument("--reconnect-delay", type=float, default=5.0, help="Seconds to wait before reconnect.")
    return p.parse_args(argv)


def main() -> None:
    args = parse_args()
    try:
        asyncio.run(
            main_async(
                device_id=args.device_id,
                device_token=args.device_token,
                duration_seconds=args.duration_seconds,
                ping_interval=args.ping_interval,
                reconnect_delay=args.reconnect_delay,
            )
        )
    except KeyboardInterrupt:
        print("Interrupted by user.", flush=True)


if __name__ == "__main__":
    main()

