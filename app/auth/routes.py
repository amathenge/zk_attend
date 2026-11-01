from flask import render_template, request, redirect, url_for, session
from . import bp_auth
from werkzeug.security import generate_password_hash, check_password_hash
from app.database import get_db, cursor_init, logger
import math, random
from datetime import datetime, timedelta
from app.sms import sendSMS

DEBUGGING = False

# create a one-time six-digit code (all numbers) randomly.
def onetime():
    # create a list of the digits we need
    digits = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    output = ""
    # pick six digits at random from the list and return those.
    # use random.random() to get a random number from 0 - 1
    # multiply by 10 to get an integer from 0 - 10
    # use math.floor() to get the integer (0 - 9)
    # use str() to change that to a string.
    for digit in range(6):
        index = math.floor(random.random() * 10)
        output += str(digits[index])

    logger(f"created OTP={output}")
    return output

# function to return True or False if elapsed time is greater than wait_time minutes.
def otp_ontime(send_time, receive_time, wait_time):
    # send_time and receive_time are datetime objects - but send_time came from the database so it needs
    # to be converted. The format of send_time is YYYY-MM-DD HH:MM:SS.sssss so we need to remove
    # the milliseconds.
    ms_offset = send_time.rfind('.')
    send_time = send_time[:ms_offset]
    send_time = datetime.strptime(send_time, '%Y-%m-%d %H:%M:%S')
    diff = receive_time - send_time
    diff = diff.total_seconds() / timedelta(minutes=1).total_seconds()
    diff = math.floor(diff)
    if diff >= wait_time:
        logger("OTP timeout")
        return False

    logger("OTP on time=OK")
    return True

@bp_auth.route("/login", methods=["GET", "POST"])
def login():
    message = session.pop('login_message', None)
    session.pop('user', None)
    session.modified = True

    if DEBUGGING:
        user = {
            'id': 1,
            'email': 'debug@localhost.net',
            'firstname': 'TonyBug',
            'lastname': 'Debugger',
            'phone': '0123456789',
            'auth': (1,2,3,4,5),
            'otp': 123456
        }        
        session['user'] = user
        session.modified = True
        logger('debug user logged in succesfully')
        return redirect(url_for('bp_home.index'))

    if request.method == "POST":
        email = request.form["email"]
        # using OTP will have to ignore this
        # password = request.form["password"]
        db = get_db()
        cur = db.cursor()
        cursor_init(cur)
        # sql = "select id, email, password, firstname, lastname, phone, auth from users where email = ?"
        sql = "select id, email, firstname, lastname, phone, auth from users where email = ?"
        cur.execute(sql, (email,))
        user_data = cur.fetchone()
        if not user_data:
            session['login_message'] = 'Invalid email or password'
            session.modified = True
            logger(f'user email={email} - login fail')
            return redirect(url_for('bp_auth.login'))
        # if not check_password_hash(user_data['password'], password):
        #     session['login_message'] = 'Invalid email or password'
        #     session.modified = True
        #     logger(f'user email={email} - login fail')
        #     return redirect(url_for('bp_auth.login'))

        auth = tuple([int(x) for x in user_data['auth']])
        user = {
            'id': int(user_data['id']),
            'email': user_data['email'],
            'firstname': user_data['firstname'],
            'lastname': user_data['lastname'],
            'phone': user_data['phone'],
            'auth': auth,
            'otp': None
        }

        session['user'] = user
        session.modified = True

        otp = onetime()
        # invalidate existing tokens
        sql = 'update otp set valid = 0 where userid = ?'
        cur.execute(sql, [user['id']])
        db.commit()
        # get current date/time for authentication
        now = datetime.now()
        # insert otp into database
        sql = 'insert into otp (userid, otp, otp_time, valid) values (?, ?, ?, ?)'
        cur.execute(sql, [user['id'], otp, now, 1])
        db.commit()
        # send OTP to user phone + email.
        message = f"Your OTP to login to the application is {otp}"
        sendSMS(message, user['phone'])
        logger(f"user id={user['id']}, email={user['email']} - otp sent")
        return render_template('auth/otp.html')

    return render_template("auth/login.html", message=message)

@bp_auth.route('/check_otp', methods=['GET','POST'])
def check_otp():
    if 'user' in session and session['user']['otp']:
        return redirect(url_for('bp_home.index'))

    now = datetime.now()
    now_string = now.strftime('%d%b%Y %H:%M:%S').upper()
    message = None
    if request.method == 'POST':
        otp = request.form['otp']
        userid = session['user']['id']
        # get OTP saved in database.
        db = get_db()
        cur = db.cursor()
        cursor_init(cur)
        sql = 'select id, userid, userid, otp, otp_time, valid from otp where userid = ? and otp = ? and valid = 1'
        cur.execute(sql, [userid, otp])
        data = cur.fetchone()
        if data is None:
            # if nothing is returned from the database, wrong OTP. Go back to login page.
            logger(f"OTP fail user={session['user']['email']}")
            message = "Invalid OTP - try again"
        else:
            # OTP was correct for this user, and is valid. Check time returned.
            if otp_ontime(data['otp_time'], now, 2):
                # response time is OK. Update login time and show the home page
                sql = 'update users set lastlogin = ? where id = ?'
                cur.execute(sql, [now, userid])
                db.commit()
                logger(f"OTP Success user={session['user']['email']}")
                session['user']['otp'] = otp
                session['modified'] = True
                logger(f"OTP successful for user id={userid} at {now_string}")
                return redirect(url_for('bp_home.index'))
            else:
                logger(f"OTP timeout user={session['user']['email']}")
                message = 'Timeout... try again'

        return render_template('auth/login.html', message=message)

    return render_template('auth/otp.html')        

@bp_auth.route("/logout")
def logout():
    if 'user' in session:
        logger(f"user {session['user']['email']} - logout")
        del session['user']
        session.modified = True

    return render_template("auth/login.html")