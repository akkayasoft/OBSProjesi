from flask import Blueprint

saglik_bp = Blueprint('saglik', __name__, template_folder='../templates/saglik')

from app.saglik.routes import register_routes  # noqa: F401, E402
register_routes(saglik_bp)
