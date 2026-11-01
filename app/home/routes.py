from . import bp_home
from flask import render_template, session, redirect, url_for, request, current_app, send_file
from app.sql_strings import sql_home
from app.database import get_db, cursor_init, logger
from app.filters import *
from datetime import datetime, timedelta
import os

def n10(item):
    if int(item[-1]) in (0, 1, 2):
        return f"{item[0]}0"
    elif int(item[-1]) in (3, 4, 5, 6, 7):
        return f"{item[0]}5"
    else:
        return f"{int(item[0])+1}0"

def logged_in():
    if 'user' not in session or not session['user']['otp']:
        return False

    return True

@bp_home.route("/")
def index():
    if 'user' not in session:
        return redirect(url_for('bp_auth.login'))

    # all users have access to the home page.
    # home page will list attendance for the last 10 days.

    db = get_db()
    cur = db.cursor()
    cursor_init(cur)
    cur.execute(sql_home)
    data = cur.fetchall()

    return render_template("home/index.html", data=data)

@bp_home.route("/reports", methods=['GET', 'POST'])
def reports():
    if not logged_in():
        return redirect(url_for('bp_auth.login'))

    auth = (HR_MANAGER, DATA_MANAGER, VIEW_ONLY, ADMIN)
    user = session['user']
    if not hasauth(user['auth'], auth):
        return redirect(request.referrer)

    staff = None
    data = None
    stafflist = None
    message = None
    db = get_db()
    cur = db.cursor()
    if request.method == "POST":
        data = []
        staff = request.form['selectstaff']
        sql = "select id, firstname || ' ' || lastname as fullname from staff where id = ?"
        cur.execute(sql, (staff,))
        staff = cur.fetchone()
        if staff is None:
            return redirect(request.referrer)
        
        staffid = staff['id']

        # print(f"id={staffid}, {staff['fullname']}")
        # sql = 'select distinct(att_date) from attendance where staff = ? order by id desc'
        sql = '''
            select distinct(att_date), 'A' as source from attendance where staff = ?
            and att_date not in (select distinct(att_date) from manual where staff = ?)
            union
            select distinct(att_date), 'B' as source from manual where staff = ?
            order by att_date desc
        '''
        cur.execute(sql, (staffid, staffid, staffid))
        records = cur.fetchall()

        for record in records:
            temp = {'att_date': record['att_date'], 'source': record['source']}
            dayofweek = datetime.strptime(record['att_date'], '%Y-%m-%d').strftime('%A')
            temp['dayofweek'] = dayofweek
            # print(f"{record['att_date']}: ", end='')
            if temp['source'] == 'A':
                sql = 'select id, att_time from attendance where staff = ? and att_date = ? order by id asc'
            else:
                sql = 'select id, att_time from manual where staff = ? and att_date = ? order by id asc'
            cur.execute(sql, (staffid,record['att_date']))
            clocks = cur.fetchall()

            # only need two clocks...
            if len(clocks) > 2:
                clocks = [clocks[0], clocks[-1]]            
            message = ''
            if len(clocks) == 2:
                start_time = clocks[0]['att_time']
                end_time = clocks[1]['att_time']
                temp['start_time'] = start_time
                temp['end_time'] = end_time
                # print(f"From {start_time} To {end_time} = ", end='')
            elif len(clocks) == 1:
                if (datetime.strptime(clocks[0]['att_time'], '%H:%M:%S') < datetime.strptime('10:00:00','%H:%M:%S')):
                    temp['start_time'] = clocks[0]['att_time']
                    temp['end_time'] = '-'
                else:
                    temp['start_time'] = '-'
                    temp['end_time'] = clocks[0]['att_time']
                message = 'Inconsistent data'
            else:
                temp['start_time'] = '-'
                temp['end_time'] = '-'
                message = 'Inconsistent data'

            if temp['source'] == 'B':
                if len(clocks) > 0:
                    sql = 'select code, description from reason where code = (select reason from manual where id = ?)'
                    cur.execute(sql, (clocks[0]['id'],))
                    reason = cur.fetchone()
                    if len(message) > 0:
                        message += f"\n{reason['code']}: {reason['description']}"
                    else:
                        message = f"Manual Data\n{reason['code']}: {reason['description']}"
                else:
                    if len(message) > 0:
                        message += "\nUnknown Error with Manual Table"
                    else:
                        message = "Unknown Error with Manual Table"

            if len(clocks) == 2:
                clock_start = datetime.strptime(start_time, '%H:%M:%S')
                clock_end = datetime.strptime(end_time, '%H:%M:%S')
                difference = clock_end - clock_start
                difference_secs = difference.total_seconds()
                if difference_secs >= 60:
                    difference_mins = (difference_secs - (difference_secs % 60)) / 60
                    difference_secs = difference_secs % 60
                else:
                    difference_mins = 0
                if difference_mins >= 60:
                    difference_hours = (difference_mins - (difference_mins % 60)) / 60
                    difference_mins = difference_mins % 60
                else:
                    difference_hours = 0
                difference_secs = int(difference_secs)
                difference_mins = int(difference_mins)
                difference_hours = int(difference_hours)
                temp['work_hours'] = f"{difference_hours:02d}H {difference_mins:02d}M {difference_secs:02d}S"
                # print(f"{difference_hours:02d} H {difference_mins:02d} M {difference_secs:02d} S")
            else:
                temp['work_hours'] = '-'
                if len(message) > 0:
                    message = 'Inconsistent data'+'\n'+message.replace('Inconsistent data', '')
                else:
                    message = 'Inconsistent data'
            if message:
                temp['message'] = message
            else:
                temp['message'] = ''
            # data goes here
            data.append(temp.copy())
            temp = {}
            message = None

        # save to database
        sql = 'delete from reports where staff = ?'
        cur.execute(sql, (staffid,))
        db.commit()
        sql = '''
            insert into reports (staff, att_date, dayofweek, start_time, end_time, work_hours, message)
            values (?, ?, ?, ?, ?, ?, ?)
        '''
        for item in data:
            cur.execute(sql, (staffid, item['att_date'], item['dayofweek'], item['start_time'], item['end_time'],
                              item['work_hours'], item['message']))
            db.commit()

        logger(f"user={user['email']} - gen report on {staff['fullname']}")

    sql = '''
        select id, firstname, lastname from staff
    '''
    cur.execute(sql)
    stafflist = cur.fetchall()
    return render_template('home/reports.html', stafflist=stafflist, data=data, staff=staff, message=message)

@bp_home.route('/exportdata/<uid>', methods=['GET', 'POST'])
def exportdata(uid):
    if not logged_in():
        return redirect(url_for('bp_auth.login'))

    auth = (HR_MANAGER, DATA_MANAGER, ADMIN)
    user = session['user']
    if not hasauth(user['auth'], auth):
        return redirect(request.referrer)

    db = get_db()
    cur = db.cursor()
    sql = '''
        select id, staff, att_date, dayofweek, start_time, end_time, work_hours, message
        from reports where staff = ?
    '''
    cur.execute(sql, (uid,))
    data = cur.fetchall()
    if len(data) == 0:
        data = None
    if data:
        sql = "select id, firstname || ' ' || lastname as fullname from staff where id = ?"
        cur.execute(sql, (uid,))
        staff = cur.fetchone()
        now = datetime.now().strftime('%d%b%Y').upper()
        sql = 'insert into reportlist (staff) values (?)'
        cur.execute(sql, (uid,))
        db.commit()
        placeholder = cur.lastrowid
        # should look for an exception here, but will just continue.
        filename = f"Attendance_{staff['fullname']}_{now}_{placeholder}" + ".csv"
        folder_path = os.path.join(current_app.root_path, current_app.config['REPORT_FOLDER'])
        f = open(os.path.join(folder_path,filename), 'w')
        for row in data:
            temp = datetime.strptime(row['att_date'],'%Y-%m-%d')
            temp = datetime.strftime(temp, '%d%b%Y').upper()
            output = str(row['id'])+','+str(row['staff'])+','+temp+','+row['dayofweek']
            output += ','+row['start_time']+','+row['end_time']+','+row['work_hours']+','+row['message']
            f.write(output+'\n')
        f.close()
        message = f"Report written to file {filename}"
        sql = 'update reportlist set filedate = ?, filename = ? where id = ?'
        cur.execute(sql, (now, filename, placeholder))
        db.commit()
        logger(f"user={user['email']} - export report on {staff['fullname']}")
    else:
        message = f"Unable to create report for staff id={uid}"

    return render_template('home/reportresult.html', message=message)

@bp_home.route('/listreports')
def listreports():
    if not logged_in():
        return redirect(url_for('bp_auth.login'))

    auth = (HR_MANAGER, DATA_MANAGER, ADMIN)
    user = session['user']
    if not hasauth(user['auth'], auth):
        return redirect(request.referrer)

    db = get_db()
    cur = db.cursor()
    sql = 'select id, staff, filedate, filename from reportlist order by id desc'
    cur.execute(sql)
    data = cur.fetchall()
    if len(data) == 0:
        data = None
    
    return render_template('home/listreports.html', reports=data)

# download a report
@bp_home.route("/reportdownload/<rid>", methods=['GET', 'POST'])
def reportdownload(rid):
    if not logged_in():
        return redirect(url_for('bp_auth.login'))

    auth = (HR_MANAGER, DATA_MANAGER, ADMIN)
    user = session['user']
    if not hasauth(user['auth'], auth):
        return redirect(request.referrer)

    db = get_db()
    cur = db.cursor()
    sql = 'select filename from reportlist where id = ?'
    cur.execute(sql, (rid,))
    data = cur.fetchone()
    if data is None:
        return render_template('home/reportresult.html', message=f"File with id={rid} does not exist")
    
    folder_path = os.path.join(current_app.root_path, current_app.config['REPORT_FOLDER'])
    if os.path.exists(os.path.join(folder_path,data['filename'])):
        message = f"Download of {data['filename']} completed"
        logger(f"user={user['email']}: "+message)
        return send_file(os.path.join(folder_path,data['filename']), as_attachment=True)

    return render_template('home/reportresult.html', message=message)

# delete a report
@bp_home.route('/reportdelete/<rid>', methods=['GET', 'POST'])
def reportdelete(rid):
    if not logged_in():
        return redirect(url_for('bp_auth.login'))

    auth = (DATA_MANAGER, ADMIN)
    user = session['user']
    if not hasauth(user['auth'], auth):
        return redirect(request.referrer)

    db = get_db()
    cur = db.cursor()
    sql = 'select filename from reportlist where id = ?'
    cur.execute(sql,(rid,))
    data = cur.fetchone()
    if data is None:
        # file does not exist
        return render_template('reportresult.html', message=f"File with id={rid} does not exist")
    # delete file from filesystem
    folder_path = os.path.join(current_app.root_path, current_app.config['REPORT_FOLDER'])
    if os.path.exists(os.path.join(folder_path,data['filename'])):
        os.remove(os.path.join(folder_path,data['filename']))
    # delete file from entry
    sql = 'delete from reportlist where id = ?'
    cur.execute(sql, (rid,))
    db.commit()
    message = f"File {data['filename']} deleted"
    logger(f"user={user['email']} "+message)
    return render_template('home/reportresult.html', message=message)

@bp_home.route("/edit_attendance", methods=['GET', 'POST'])
def edit_attendance():
    if not logged_in():
        return redirect(url_for('bp_auth.login'))

    auth = (HR_MANAGER, DATA_MANAGER, ADMIN)
    user = session['user']

    if not hasauth(user['auth'], auth):
        return redirect(request.referrer)

    # present list of people and then a form to select the dates to edit
    db = get_db()
    cur = db.cursor()
    if request.method == "POST":
        staff = int(request.form.get('selectstaff'))
        if staff == 0:
            return redirect(request.referrer)
        sql = '''select min(id) id, staff, att_date, min(att_time) clock_in, max(att_time) clock_out,
            'A' source, NULL reason from attendance where staff = ?
            and att_date not in (select distinct(att_date) from manual where staff = ?)
            group by staff, att_date
            union
            select min(id) id, staff, att_date, min(att_time) clock_in, max(att_time) clock_out,
            'B' source, reason from manual where staff = ?
            group by staff, att_date
            order by att_date desc
        '''
        cur.execute(sql, (staff,staff, staff))
        data = cur.fetchall()
        staffname = None
        attendance = None
        if len(data) == 0:
            data = None
        else:
            # clean up data - when only one clock, it's both min() and max()
            attendance = []
            temp_row = None
            for row in data:
                temp_row = dict(row)
                if row['clock_in'] == row['clock_out']:
                    dt = datetime.strptime(row['clock_in'], '%H:%M:%S')
                    if dt <= datetime.strptime('10:00:00', '%H:%M:%S'):
                        temp_row['clock_out'] = None
                    else:
                        temp_row['clock_in'] = None
                attendance.append(temp_row.copy()) 
            sql = 'select id, firstname, lastname from staff where id = ?'
            cur.execute(sql, (staff,))
            staffname = cur.fetchone()
        return render_template('home/edit_attendance.html', attendance=attendance, staffname=staffname)

    sql = 'select id, firstname, lastname from staff'
    cur.execute(sql)
    data = cur.fetchall()
    return render_template('home/edit_selectstaff.html', staff=data)

@bp_home.route('/edit_item/<sid>/<did>/<tid>')
def edit_item(sid, did, tid):
    if not logged_in():
        return redirect(url_for('bp_auth.login'))

    auth = (DATA_MANAGER, HR_MANAGER, ADMIN)
    user = session['user']

    if not hasauth(user['auth'], auth):
        return redirect(request.referrer)

    db = get_db()
    cur = db.cursor()
    tablename = None
    if tid == 'A':
        tablename = 'attendance'
    else:
        tablename = 'manual'
    sql = f'''
        select id, staff, att_date, att_time from {tablename} where staff = ?
        and att_date = ?
    '''

    cur.execute(sql, (sid,did))
    # data = cur.fetchone()
    clock_in_hour = "00"
    clock_in_minute = "00"
    clock_out_hour = "00"
    clock_out_minute = "00"
    data = cur.fetchall()
    if len(data) > 2:
        data = [data[0], data[-1]]
    if len(data) == 0:
        data = None
    elif len(data) == 1:    # if time < 10:00AM, assume clock-in. 
        row = data[0]
        clock_in_hour = row['att_time'].split(':')[0]
        clock_in_minute = row['att_time'][row['att_time'].find(':')+1:row['att_time'].rfind(':')]
        clock_out_hour = "00"
        clock_out_minute = "00"
        if int(clock_in_hour) >= 10:
            clock_out_hour = clock_in_hour
            clock_out_minute = clock_in_minute
            clock_in_hour = "00"
            clock_in_minute = "00"
    elif len(data) == 2:
        row = data[0]
        clock_in_hour = row['att_time'].split(':')[0]
        clock_in_minute = row['att_time'][row['att_time'].find(':')+1:row['att_time'].rfind(':')]
        row = data[1]
        clock_out_hour = row['att_time'].split(':')[0]
        clock_out_minute = row['att_time'][row['att_time'].find(':')+1:row['att_time'].rfind(':')]
    else:
        clock_in_hour = "00"
        clock_in_minute = "00"
        clock_out_hour = "00"
        clock_out_minute = "00"

    staff = None
    clock_data = {
        'tablename': tablename,
        'clock_in_hour': clock_in_hour,
        'clock_in_minute': n10(clock_in_minute),
        'clock_out_hour': clock_out_hour,
        'clock_out_minute': n10(clock_out_minute)
    }
    if data:
        sql = 'select id, firstname, lastname from staff where id = ?'
        cur.execute(sql, (sid,))
        staff = cur.fetchone()
    sql = 'select id, code, description from reason'
    cur.execute(sql)
    reasons = cur.fetchall()

    return render_template('home/edit_item.html', att_record=data, staff=staff, clock_data=clock_data, reasons=reasons)

@bp_home.route('/save_item', methods=['GET', 'POST'])
def save_item():
    if not logged_in():
        return redirect(url_for('bp_auth.login'))

    auth = (DATA_MANAGER, HR_MANAGER, ADMIN)
    user = session['user']

    if not hasauth(user['auth'], auth):
        return redirect(request.referrer)

    if request.method == "POST":
        if request.form['submit'] == "cancel":
            return redirect(url_for('bp_home.edit_attendance'))

        # collect form data
        staff = int(request.form['staff'])
        att_date = request.form['att_date']
        # att_date looks like DDMMMYYYY, need to fix it to YYYY-MM-DD
        att_date = datetime.strptime(att_date, '%d%b%Y').strftime('%Y-%m-%d')
        clock_in_hour = request.form.get('clock_in_hour')
        clock_in_minute = request.form.get('clock_in_minute')
        clock_out_hour = request.form.get('clock_out_hour')
        clock_out_minute = request.form.get('clock_out_minute')
        reason = request.form.get('reason')
        tablename = request.form['tablename']

        clock_in = f"{clock_in_hour}:{clock_in_minute}:00"
        clock_out = f"{clock_out_hour}:{clock_out_minute}:00"

        savedata = {
            'staff': staff,
            'att_date': att_date,
            'clock_in': clock_in,
            'clock_out': clock_out,
            'reason': reason,
            'tablename': tablename
        }

        db = get_db()
        cur = db.cursor()
        sql = 'select id, firstname, lastname from staff where id = ?'
        cur.execute(sql, (staff,))
        data = cur.fetchone()
        staff =  {
            'id': staff,
            'firstname': data['firstname'],
            'lastname': data['lastname']
        }

        if request.form['submit'] == 'delete':
            return render_template('home/delete_confirm.html', att_record=savedata, staff=staff)


        return render_template('home/save_confirm.html', att_record=savedata, staff=staff)
    
    # if this didn't come from a POST, send it back to where it came from
    return redirect(request.referrer)

@bp_home.route('/save_attendance', methods=['GET', 'POST'])
def save_attendance():
    if not logged_in():
        return redirect(url_for('bp_auth.login'))

    auth = (DATA_MANAGER, HR_MANAGER, ADMIN)
    user = session['user']

    if not hasauth(user['auth'], auth):
        return redirect(request.referrer)

    db = get_db()
    cur = db.cursor()
    if request.method == "POST":
        if 'cancel' not in request.form['submit']:
            staff = int(request.form['staff'])
            att_date = request.form['att_date']
            clock_in = request.form['clock_in']
            clock_out = request.form['clock_out']
            reason = request.form['reason']
            # tablename = request.form['tablename']
            # sql = f"delete from {tablename} where att_date = ?"
            sql = f"delete from manual where att_date = ? and staff = ?"
            cur.execute(sql, (att_date, staff))
            db.commit()
            # all changes should go to the manual table.
            sql = f'''
                insert into manual (staff, att_date, att_time, reason)
                values (?, ?, ?, ?)
            '''
            cur.execute(sql, (staff, att_date, clock_in, reason))
            db.commit()
            cur.execute(sql, (staff, att_date, clock_out, reason))
            db.commit()
            logger(f"email={user['email']} - attendance update for staff id={staff} for date={att_date}")
        
    return redirect(url_for('bp_home.index'))

@bp_home.route('/delete_attendance', methods=['GET', 'POST'])
def delete_attendance():
    if not logged_in():
        return redirect(url_for('bp_auth.login'))

    auth = (DATA_MANAGER, HR_MANAGER, ADMIN)
    user = session['user']

    if not hasauth(user['auth'], auth):
        return redirect(request.referrer)

    db = get_db()
    cur = db.cursor()
    if request.method == "POST":
        if 'cancel' not in request.form['submit']:
            staff = int(request.form['staff'])
            att_date = request.form['att_date']
            clock_in = request.form['clock_in']
            clock_out = request.form['clock_out']
            reason = request.form['reason']
            # tablename = request.form['tablename']
            # sql = f"delete from {tablename} where att_date = ?"
            sql = f"delete from manual where att_date = ? and staff = ?"
            cur.execute(sql, (att_date, staff))
            db.commit()
            sql = 'select id, code, description from reason where code = ?'
            cur.execute(sql, (reason,))
            reason_data = cur.fetchone()
            sql = 'select id, firstname, lastname from staff where id = ?'
            cur.execute(sql, (staff,))
            staff_data = cur.fetchone()
            
            att_data = {
                'id': staff,
                'staff_name': f"{staff_data['firstname']} {staff_data['lastname']}",
                'att_date': att_date,
                'clock_in': clock_in,
                'clock_out': clock_out,
                'reason_code': reason,
                'reason_description': reason_data['description'],
                'table': 'manual'
            }
            message = f'Successfully deleted record for date {att_date}'
            logger(f"user={user['email']} - deleted manual clocks for staff={att_data['staff_name']} for date={att_data['att_date']}")
            return render_template('home/deleteresult.html', att_data=att_data, message=message)
                                   
        
    return redirect(url_for('bp_home.index'))

@bp_home.route('/add_new_record/<sid>', methods=['GET', 'POST'])
def add_new_record(sid):
    if not logged_in():
        return redirect(url_for('bp_auth.login'))

    auth = (DATA_MANAGER, HR_MANAGER, ADMIN)
    user = session['user']

    if not hasauth(user['auth'], auth):
        return redirect(request.referrer)

    # figure out the gaps and only give an option to add where there's a gap.
    # otherwise update/overwrite existing records.
    db = get_db()
    cur = db.cursor()
    # missing dates, including Sundays, from the earliest date, to today.
    # also check the manual table...
    sql = '''
        select min(id) mid, att_date from attendance where staff = ? group by att_date
        union
        select min(id) mid, att_date from manual where staff = ? group by att_date
        order by att_date asc
    '''
    cur.execute(sql, (sid,sid))
    data = cur.fetchall()
    if len(data) == 0:
        data = None

    temp = []
    date_collection = []
    missing_dates = []
    if data:
        for row in data:
            temp.append(row['att_date'][:])

        for item in temp:
            date_collection.append(datetime.strptime(item, '%Y-%m-%d'))

        
        first_date = date_collection[0]
        # can possibly allow to go to the current date...
        # last_date = datetime.now()
        last_date = date_collection[len(date_collection)-1]

        cur_date = first_date + timedelta(days=1)
        while cur_date < last_date:
            if cur_date not in date_collection:
                missing_dates.append({'att_date': cur_date})

            cur_date = cur_date + timedelta(days=1)

    sql = 'select id, firstname, lastname from staff where id = ?'
    cur.execute(sql, (sid,))
    staff = cur.fetchone()
    if staff is None:
        return redirect(request.referrer)

    sql = 'select id, code, description from reason'
    cur.execute(sql)
    reasons = cur.fetchall()
    if len(reasons) == 0:
        reasons = None

    return render_template('home/add_new_clock.html', missing_dates=missing_dates, staff=staff, reasons=reasons)

@bp_home.route('/add_clock', methods=['GET', 'POST'])
def add_clock():
    if not logged_in():
        return redirect(url_for('bp_auth.login'))

    auth = (HR_MANAGER, DATA_MANAGER, ADMIN)
    user = session['user']

    if not hasauth(user['auth'], auth):
        return redirect(request.referrer)

    db = get_db()
    cur = db.cursor()

    if request.method == "POST":
        if 'cancel' not in request.form['submit']:
            sid = int(request.form['staff'])
            att_date = request.form.get('att_date')
            clock_in_hour = request.form.get('clock_in_hour')
            clock_in_minute = request.form.get('clock_in_minute')
            clock_out_hour = request.form.get('clock_out_hour')
            clock_out_minute = request.form.get('clock_out_minute')
            reason = request.form.get('reason')

            sql = 'select id, firstname, lastname from staff where id = ?'
            cur.execute(sql, (sid,))
            staff = cur.fetchone()

            clock_in = f"{clock_in_hour}:{clock_in_minute}:00"
            clock_out = f"{clock_out_hour}:{clock_out_minute}:00"

            savedata = {
                'staff': staff['id'],
                'att_date': att_date,
                'clock_in': clock_in,
                'clock_out': clock_out,
                'reason': reason
            }

            return render_template('home/add_clock_confirm.html', att_record=savedata, staff=staff)
        else:
            return redirect(url_for('bp_home.edit_attendance'))
    
    return redirect(url_for('bp_home.edit_attendance'))

@bp_home.route('/save_clocks', methods=['GET', 'POST'])
def save_clocks():
    if not logged_in():
        return redirect(url_for('bp_auth.login'))

    auth = (HR_MANAGER, DATA_MANAGER, ADMIN)
    user = session['user']

    if not hasauth(user['auth'], auth):
        return redirect(request.referrer)

    db = get_db()
    cur = db.cursor()

    if request.method == "POST":
        if 'cancel' not in request.form['submit']:
            staff = request.form['staff']
            att_date = request.form['att_date']
            clock_in = request.form['clock_in']
            clock_out = request.form['clock_out']
            reason = request.form['reason']

            sql = '''
                insert into manual (staff, att_date, att_time, reason)
                values (?, ?, ?, ?)
            '''

            cur.execute(sql, (staff, att_date, clock_in, reason))
            db.commit()
            cur.execute(sql, (staff, att_date, clock_out, reason))
            db.commit()
            logger(f"user={user['email']} - new attendance record for staff id={staff} for date={att_date}")

    return redirect(url_for('bp_home.index'))

