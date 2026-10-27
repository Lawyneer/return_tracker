"""Tax Return Status Tracker — application factory and entry point.

Run with:  python app.py
"""
import sys
import logging
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config
from db import close_db, init_db
from helpers import register_template_helpers
from auth import auth_bp
from returns import returns_bp

csrf = CSRFProtect()


def create_app(config_object=Config):
    """Build and configure the Flask application."""
    if not config_object.SECRET_KEY:
        sys.exit("FATAL: TAX_TRACKER_SECRET environment variable is not set.\n"
                 "Generate one with:  python -c \"import secrets; print(secrets.token_hex(32))\"")

    app = Flask(__name__)
    app.config.from_object(config_object)

    # Trust one proxy hop (nginx) so request.remote_addr is the real client
    # IP for lockout tracking. Configure nginx to pass X-Forwarded-For.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

    # Database: ensure schema/seed data exist, close connections per request.
    init_db()
    app.teardown_appcontext(close_db)

    # CSRF protection for all POST forms.
    csrf.init_app(app)

    # Template context + filters, then route blueprints.
    register_template_helpers(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(returns_bp)
    return app


if __name__ == "__main__":
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app = create_app()
    # NOTE: for production, run under gunicorn/uwsgi behind nginx instead,
    # e.g.: gunicorn -w 2 -b 127.0.0.1:5000 app:create_app()
    app.run(host="127.0.0.1", port=5000, debug=False)
