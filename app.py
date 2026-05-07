from flask import Flask

from routes.home import home_bp
from routes.dashboard import dashboard_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object("config")
    app.register_blueprint(home_bp)
    app.register_blueprint(dashboard_bp)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
