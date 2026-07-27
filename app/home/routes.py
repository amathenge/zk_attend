from . import bp_home
from flask import render_template


@bp_home.route("/")
def index():
    return render_template("home/index.html")
