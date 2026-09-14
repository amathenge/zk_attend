from flask import render_template, request, redirect, url_for, session
from . import bp_auth
from werkzeug.security import generate_password_hash, check_password_hash
from app.database import get_db, cursor_init

@bp_auth.route("/login", methods=["GET", "POST"])
def login():
    message = session.pop('login_message', None)
    session.pop('user', None)
    session.modified = True

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        db = get_db()
        cur = db.cursor()
        cursor_init(cur)
        sql = "select id, email, password, firstname, lastname, phone, auth from users where email = ?"
        cur.execute(sql, (email,))
        user_data = cur.fetchone()
        if not user_data:
            session['login_message'] = 'Invalid email or password'
            session.modified = True
            return redirect(url_for('bp_auth.login'))
        if not check_password_hash(user_data['password'], password):
            session['login_message'] = 'Invalid email or password'
            session.modified = True
            return redirect(url_for('bp_auth.login'))

        # it's all OK
        auth = tuple([int(x) for x in user_data['auth']])
        user = {
            'id': int(user_data['id']),
            'email': user_data['email'],
            'firstname': user_data['firstname'],
            'lastname': user_data['lastname'],
            'phone': user_data['phone'],
            'auth': auth
        }

        session['user'] = user
        session.modified = True

        return redirect(url_for('bp_home.index'))

    return render_template("auth/login.html", message=message)

@bp_auth.route("/logout")
def logout():
    if 'user' in session:
        del session['user']
        session.modified = True

    return render_template("auth/login.html")