from . import bp_data
from flask import render_template, session, redirect, url_for, request, current_app, send_file
from app.sql_strings import sql_import, sql_import_attend
from app.database import get_db, cursor_init, logger
from app.filters import *
from datetime import datetime, timedelta
from pyzk2 import ZK, const

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

def logged_in():
    if 'user' not in session or not session['user']['otp']:
        return False

    return True

@bp_data.route('/importsetup')
def importsetup():
    if 'user' not in session:
        return redirect(url_for('bp_auth.login'))

    logger(f"user={session['user']['email']} import request")
    return render_template('data/importsetup.html')

@bp_data.route('/importdata', methods=['GET'])
def importdata():
    if 'user' not in session:
        return redirect(url_for('bp_auth.login'))
        
    zk = ZK(DEVICE_IP, port=DEVICE_PORT, timeout=5, password=0, force_udp=False, ommit_ping=True)

    punch_mapping = {
        0: "Check Out",
        1: "Check In",
        2: "Break Out",
        3: "Break In"
    }

    conn = None
    now = datetime.now()
    date_now = now.strftime('%Y-%m-%d')
    time_now = now.strftime('%H:%M:%S')
    message = None
    importsuccess = False

    try:
        logger(f'Connecting to ZKTeco K40 at {DEVICE_IP}...')
        conn = zk.connect()

        # Disable device during operations to prevent users from clocking in/out
        conn.disable_device()
        logger('Device connected and temporarily disabled.')

        db = get_db()
        cur = db.cursor()
        cursor_init(cur)

        sql = sql_import

        logger('--- Fetching Attendance Logs ---')
        attendances = conn.get_attendance()
        for record in attendances:
            att_date = record.timestamp.strftime('%Y-%m-%d')
            att_time = record.timestamp.strftime('%H:%M:%S')
            cur.execute(sql_import, [date_now, time_now] + 
                        [record.user_id, att_date, att_time,
                        record.status, record.punch])
            db.commit()

        # update the attendance table
        sql = sql_import_attend
        cur.execute(sql_import_attend)
        db.commit()


    except Exception as e:
        logger(f'An error occurred: {e}')
        message = f'Error {e}<br>Please Try Again'
        importsuccess = False
        logger(f"user={session['user']['email']} - import failed")

    finally:
        if conn:
            # Re-enable the device before closing the link
            conn.enable_device()
            conn.disconnect()
            logger('Disconnected safely from device.')
            importsuccess = True
            logger(f"user={session['user']['email']} - import success")

        if not message:
            message = 'Upload of Attendance Data completed'

    return render_template('data/importresult.html', message=message, importsuccess=importsuccess)
