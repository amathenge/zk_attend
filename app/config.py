import os
from datetime import timedelta

class Config(object):
    DEBUG = True
    DEVELOPMENT = True
    SECRET_KEY = os.urandom(24)
    UPLOAD_FOLDER = 'files'
    REPORT_FOLDER = 'reports'
    # max upload = 10 MB (in bytes)
    MAX_CONTENT_PATH = 10 * 1024 * 1024

class Default(Config):
    DEBUG = False

class Production(Config):
    DEBUG = False
    DEVELOPMENT = False
    SECRET_KEY = '5ae9ce4a61acdee13508aa211ccc883d1625adbc6dbed53b'
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=15)
    SESSION_REFRESH_EACH_REQUEST = True