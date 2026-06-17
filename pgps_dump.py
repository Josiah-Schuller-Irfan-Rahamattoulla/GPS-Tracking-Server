import os

import requests


def main() -> None:
    base = os.getenv("TEST_BASE_URL", "https://gpstracking.josiahschuller.au").rstrip("/")
    device_id = int(os.getenv("TEST_DEVICE_ID", "67"))
    token = os.getenv("TEST_DEVICE_TOKEN", "sim_device_12345_123456789")

    url = f"{base}/v1/pgps"
    params = {
        "device_id": device_id,
        "prediction_count": 8,
        "prediction_period_min": 120,
    }
    headers = {"Access-Token": token}

    r = requests.get(url, params=params, headers=headers, timeout=90)
    print("STATUS", r.status_code)

    body = r.content
    print("BODY_LEN", len(body))

    if r.status_code != 200:
        print("BODY_TEXT", r.text[:500])
        return

    print("CONTENT_TYPE", r.headers.get("Content-Type"))
    print("X_PGPS_SOURCE", r.headers.get("X-PGPS-Source"))
    print("BODY_HEAD_HEX", body[:64].hex())


if __name__ == "__main__":
    main()
