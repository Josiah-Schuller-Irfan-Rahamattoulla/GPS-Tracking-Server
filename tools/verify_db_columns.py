import os

import psycopg2


def main() -> None:
    uri = os.environ.get("DATABASE_URI")
    if not uri:
        raise SystemExit("DATABASE_URI is not set")

    def fetch_columns(cur, table: str) -> list[str]:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name=%s
            ORDER BY ordinal_position
            """,
            (table,),
        )
        return [r[0] for r in cur.fetchall()]

    conn = psycopg2.connect(uri)
    try:
        with conn.cursor() as cur:
            print("devices cols:", fetch_columns(cur, "devices"))
            print("gps_data cols:", fetch_columns(cur, "gps_data"))
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema='public'
                  AND table_name IN ('geofences')
                ORDER BY table_name
                """
            )
            print("tables:", [r[0] for r in cur.fetchall()])
    finally:
        conn.close()


if __name__ == "__main__":
    main()

