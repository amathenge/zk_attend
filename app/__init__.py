from flask import Flask

def create_app(conf = None):
    app = Flask(__name__)

    if conf:
        app.config.from_object(conf)
    else:
        app.config.from_object('app.config.Config')

    from app.home import bp_home
    app.register_blueprint(bp_home, url_prefix="/")

    return app

if __name__ == "__main__":
    app = create_app()
    app.run()
