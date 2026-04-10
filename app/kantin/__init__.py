from flask import Blueprint

kantin_bp = Blueprint('kantin', __name__, template_folder='../templates/kantin')

from app.kantin.routes import register_routes  # noqa: F401, E402
register_routes(kantin_bp)
