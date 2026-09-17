from pyzk2 import ZK, const
import sqlite3
from sql_strings import sql_import
from datetime import datetime

DEVICE_IP = '192.168.1.201'
DEVICE_PORT = 4370

"""
    The Attendance module/object has the following fields:
    user_id = id of user
    timestamp = ISO datetime [YYYY-MM-DD HH:MM:SS]
    status = 1=fingerprint (so always 1 for our implementation)
           = 0=PIN or password (we don't use this one)
    punch = 0=check_out, 1=check_in
"""


zk = ZK(DEVICE_IP, port=DEVICE_PORT, timeout=5, password=0, force_udp=False)
conn = None

punch_mapping = {
    0: "Check Out",
    1: "Check In",
    2: "Break Out",
    3: "Break In"
}

db = None
conn = None
now = datetime.now()
date_now = now.strftime('%Y-%m-%d')
time_now = now.strftime('%H:%M:%S')

try:
    print(f"Connecting to ZKTeco K40 at {DEVICE_IP}...")
    conn = zk.connect()

    # Disable device during operations to prevent users from clocking in/out
    conn.disable_device()
    print("Device connected and temporarily disabled.")

    db = sqlite3.connect('zk.db')
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    cur.execute('PRAGMA journal_mode=WAL;')
    cur.execute('PRAGMA synchronous=NORMAL;')

    sql = sql_import

    print("\n--- Fetching Attendance Logs ---")
    attendances = conn.get_attendance()
    for record in attendances:
        att_date = record.timestamp.strftime('%Y-%m-%d')
        att_time = record.timestamp.strftime('%H:%M:%S')
        cur.execute(sql_import, [date_now, time_now] + 
                    [record.user_id, att_date, att_time,
                     record.status, record.punch])
        db.commit()


except Exception as e:
    print(f"An error occurred: {e}")

finally:
    if conn:
        # Re-enable the device before closing the link
        conn.enable_device()
        conn.disconnect()
        print("\nDisconnected safely from device.")

    if db:
        db.close()