import os
from datetime import datetime, timedelta, timezone

import psycopg2


def main() -> None:
    uri = os.environ.get("DATABASE_URI")
    if not uri:
        raise SystemExit("DATABASE_URI is not set")

    now = datetime.now(timezone.utc)
    since = now - timedelta(minutes=10)

    conn = psycopg2.connect(uri)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT device_id, time, latitude, longitude
                FROM gps_data
                WHERE time >= %s
                ORDER BY time DESC
                LIMIT 25
                """,
                (since,),
            )
            rows = cur.fetchall()
            for r in rows:
                print(r)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

