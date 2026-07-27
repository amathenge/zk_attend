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


zk = ZK(DEVICE_IP, port=DEVICE_PORT, timeout=5, password=0, force_udp=False)
conn = None

punch_mapping = {
    0: "Check Out",
    1: "Check In",
    2: "Break Out",
    3: "Break In"
}

try:
    print(f"Connecting to ZKTeco K40 at {DEVICE_IP}...")
    conn = zk.connect()

    # Disable device during operations to prevent users from clocking in/out
    conn.disable_device()
    print("Device connected and temporarily disabled.")

    attend_file = open('attend.csv', 'w')
    user_file = open('users.csv', 'w')

    # 1. Fetch Firmware Version
    firmware = conn.get_firmware_version()
    print(f"Firmware Version: {firmware}")

    # 2. Get All Registered Users
    print("\n--- Fetching Users ---")
    users = conn.get_users()
    for user in users:
        privilege = 'User'
        if user.privilege == const.USER_ADMIN:
            privilege = 'Admin'
#        user_file.write(f'+ UID #{user.uid}\n')
        user_file.write(f'{user.user_id},{user.name}\n')
#        user_file.write(f'  Name       : {user.name}\n')
#        user_file.write(f'  Privilege  : {privilege}\n')
#        user_file.write(f'  Password   : {user.password}\n')
#        user_file.write(f'  Group ID   : {user.group_id}\n')
#        user_file.write(f'  User  ID   : {user.user_id}\n')
#        print(f"ID: {user.user_id} | Name: {user.name} | Privilege: {user.privilege}")



    # 3. Get Attendance Records
    print("\n--- Fetching Attendance Logs ---")
    attendances = conn.get_attendance()
    for record in attendances:
        # print(f"User ID: {record.user_id} | Timestamp: {record.timestamp} | Status: {record.status}")
        attend_file.write(f"{record.user_id},{record.timestamp},{record.status},{record.punch}\n")

    # attend_file.write('\n\nRAW ATTENDANCE DATA\n\n')
    # for record in attendances:
    #     attend_file.write(str(record))
    #     attend_file.write('\n')

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    if conn:
        # Re-enable the device before closing the link
        conn.enable_device()
        conn.disconnect()
        print("\nDisconnected safely from device.")

    attend_file.close()
    user_file.close()
