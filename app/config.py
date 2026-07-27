import os

class Config(object):
    DEBUG = True
    DEVELOPMENT = True
    SECRET_KEY = os.urandom(24)

class Default(Config):
    DEBUG = False
