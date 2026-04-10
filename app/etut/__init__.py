from flask import Blueprint

etut_bp = Blueprint('etut', __name__, template_folder='../templates/etut')

from app.etut.routes import register_routes  # noqa: F401, E402
register_routes(etut_bp)
