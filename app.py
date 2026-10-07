"""Tax Return Status Tracker — application factory and entry point.

Run with:  python app.py
"""
from flask import Flask
from config import Config
from db import close_db, init_db
from helpers import register_template_helpers
from auth import auth_bp
from returns import returns_bp


def create_app(config_object=Config):
    """Build and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_object)

    # Database: ensure schema/seed data exist, close connections per request.
    init_db()
    app.teardown_appcontext(close_db)

    # Template context + filters, then route blueprints.
    register_template_helpers(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(returns_bp)
    return app


app = create_app()

if __name__ == "__main__":
    # host="0.0.0.0" makes it reachable from other machines on your LAN.
    app.run(host="0.0.0.0", port=5000, debug=False)