from flask import Flask
from flask_login import LoginManager
from flask_wtf import CSRFProtect

from routes.home import home_bp
from routes.dashboard import dashboard_bp
from routes.portfolio import portfolio_bp
from routes.auth import auth_bp
from models import db, User


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object("config")

    # Initialize extensions
    db.init_app(app)
    CSRFProtect(app)

    # Initialize login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(portfolio_bp)

    # Create database tables
    with app.app_context():
        try:
            db.create_all()
        except Exception:
            app.logger.exception('Failed to initialize database schema')

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5002)
