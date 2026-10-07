"""Shared utilities, template context globals, and custom Jinja filters."""
from datetime import datetime
from flask import session
from db import get_db
from constants import RETURN_TYPES, DEFAULT_THEME


def current_user_id():
    """Return the logged-in user's id, or None."""
    return session.get("user_id")


def parse_date(s):
    """Accept YYYY-MM-DD or MM/DD/YYYY and return ISO format, or None."""
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def register_template_helpers(app):
    """Attach context processors and Jinja filters to the app."""

    @app.context_processor
    def inject_globals():
        """Make frequently needed data available in every template
        without passing it through each render call."""
        db = get_db()
        return {
            "statuses": db.execute("SELECT * FROM statuses ORDER BY stage_order").fetchall(),
            "username": session.get("username"),
            "theme": session.get("theme", DEFAULT_THEME),
            "return_types": RETURN_TYPES,
        }

    @app.template_filter("status_color")
    def status_color(stage_order, total_stages=13):
        """Map a stage order (1..13) onto a red->green HSL gradient.
        Lightness is tuned per theme so text contrast stays readable."""
        stage_order = min(stage_order, total_stages)
        hue = round((stage_order - 1) / (total_stages - 1) * 120)  # 0=red .. 120=green
        lightness = 42 if session.get("theme", DEFAULT_THEME) == "light" else 52
        return f"hsl({hue}, 65%, {lightness}%)"