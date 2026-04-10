from flask import Blueprint

davranis_bp = Blueprint('davranis', __name__, template_folder='../templates/davranis')

from app.davranis.routes import register_routes  # noqa: F401, E402
register_routes(davranis_bp)
