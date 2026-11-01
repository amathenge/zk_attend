from flask import Blueprint

bp_data = Blueprint("bp_data", __name__, static_folder="static", template_folder="templates")
from . import routes
