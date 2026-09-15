import os

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
