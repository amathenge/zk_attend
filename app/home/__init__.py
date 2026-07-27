from flask import Blueprint

bp_home = Blueprint("bp_home", __name__, static_folder="static", template_folder="templates")
from . import routes
