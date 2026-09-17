from . import bp_home
from flask import render_template, session, redirect, url_for
from app.sql_strings import sql_home

@bp_home.route("/")
def index():
    if 'user' not in session:
        return redirect(url_for('bp_auth.login'))

    # all users have access to the home page.
    # home page will list attendance for the last 10 days.

    return render_template("home/index.html")

@bp_home.route("/reports")
def reports():
    return render_template("home/under_construction.html", message="Time Reports")

@bp_home.route("/downloads")
def downloads():
    return render_template("home/under_construction.html", message="Download Reports")

@bp_home.route("/edit_attendance")
def edit_attendance():
    return render_template("home/under_construction.html", message="Edit Attendance")

@bp_home.route("/import_data")
def import_data():
    return render_template("home/under_construction.html", message="Import Data from ZkTeco")

