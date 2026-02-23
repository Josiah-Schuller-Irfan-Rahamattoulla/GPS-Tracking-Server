import os
import psycopg2

DATABASE_URI = os.getenv("DATABASE_URI", "postgresql://gpsuser:gpspassword@localhost:5433/gps_tracking")

def add_device():
    conn = psycopg2.connect(DATABASE_URI)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO devices (device_id, access_token, sms_number, name)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (device_id) DO UPDATE SET access_token = EXCLUDED.access_token, sms_number = EXCLUDED.sms_number, name = EXCLUDED.name
                """, (
                    67,
                    "sim_device_12345_123456789",
                    "+61412345678",
                    "nRF9151-GPS-Tracker"
                ))
                print("Device added or updated.")
    finally:
        conn.close()

if __name__ == "__main__":
    add_device()
