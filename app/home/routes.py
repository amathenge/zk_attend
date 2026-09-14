from . import bp_home
from flask import render_template, session, redirect, url_for


@bp_home.route("/")
def index():
    if 'user' not in session:
        return redirect(url_for('bp_auth.login'))

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

