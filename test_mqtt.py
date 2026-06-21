#!/usr/bin/env python3
"""
Manual MQTT controls subscriber test (TLS port 8883).

Usage:
  python test_mqtt.py --device-id 67 --token YOUR_DEVICE_ACCESS_TOKEN \\
      --ca mosquitto/config/certs/ca.crt

Subscribe only (wait for server publish after PUT /controls):
  python test_mqtt.py --device-id 67 --token TOKEN --ca mosquitto/config/certs/ca.crt

Publish a test payload locally (requires broker on 8883):
  python test_mqtt.py --device-id 67 --token TOKEN --ca mosquitto/config/certs/ca.crt --publish-test
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import time

import paho.mqtt.client as mqtt


def main() -> int:
    parser = argparse.ArgumentParser(description="MQTT device controls test client")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8883)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--token", required=True, help="Device access_token (MQTT password)")
    parser.add_argument("--ca", required=True, help="Path to Mosquitto CA cert (ca.crt)")
    parser.add_argument("--topic-prefix", default="devices")
    parser.add_argument("--publish-test", action="store_true")
    parser.add_argument("--wait-sec", type=int, default=30)
    args = parser.parse_args()

    topic = f"{args.topic_prefix}/{args.device_id}/controls"

    def on_connect(client, userdata, flags, reason_code, properties=None):
        print(f"connected rc={reason_code}")
        client.subscribe(topic, qos=1)
        print(f"subscribed {topic} qos=1")

        if args.publish_test:
            payload = {
                "type": "device_control_response",
                "device_id": int(args.device_id),
                "control_1": True,
                "control_2": False,
                "control_3": False,
                "control_4": False,
                "control_version": 1,
                "last_applied_control_version": 0,
                "command_pending": True,
                "timestamp": int(time.time() * 1000),
            }
            client.publish(topic, json.dumps(payload), qos=1, retain=True)
            print(f"published test payload to {topic}")

    def on_message(client, userdata, msg):
        print(f"message topic={msg.topic} retain={msg.retain} payload={msg.payload.decode()}")

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(username=str(args.device_id), password=args.token)
    client.tls_set(ca_certs=args.ca, cert_reqs=ssl.CERT_REQUIRED)
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"connecting {args.host}:{args.port} user={args.device_id}")
    client.connect(args.host, args.port, keepalive=60)
    client.loop_start()
    try:
        time.sleep(max(1, args.wait_sec))
    finally:
        client.loop_stop()
        client.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
