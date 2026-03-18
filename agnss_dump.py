import os

import requests


def main() -> None:
    base = os.getenv("TEST_BASE_URL", "https://gpstracking.josiahschuller.au").rstrip("/")
    device_id = int(os.getenv("TEST_DEVICE_ID", "67"))
    token = os.getenv("TEST_DEVICE_TOKEN", "sim_device_12345_123456789")

    url = f"{base}/v1/agnss"
    params = {"device_id": device_id}
    headers = {"Access-Token": token}

    r = requests.get(url, params=params, headers=headers, timeout=20)
    print("STATUS", r.status_code)

    body = r.content
    print("BODY_LEN", len(body))

    # Show first 64 bytes as hex so we can see if it looks like valid nRF Cloud A‑GNSS binary.
    head = body[:64]
    print("BODY_HEAD_HEX", head.hex())


if __name__ == "__main__":
    main()

