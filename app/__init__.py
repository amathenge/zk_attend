from flask import Flask
import os
from . import filters

def create_app(conf = None):
    app = Flask(__name__)
    filters.filters_init(app)

    if conf:
        app.config.from_object(conf)
    else:
        app.config.from_object('app.config.Config')

    app.config["DATABASE_DB"] = os.path.join(os.path.abspath(app.root_path), 'zk.db')
    from .database import init_db
    init_db(app)

    from .home import bp_home
    app.register_blueprint(bp_home, url_prefix="/")

    from .auth import bp_auth
    app.register_blueprint(bp_auth, url_prefix="/auth")

    return app

if __name__ == "__main__":
    app = create_app()
    app.run()
