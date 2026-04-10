from flask import Blueprint

duyurular_bp = Blueprint('duyurular', __name__, template_folder='../templates/duyurular')

from app.duyurular.routes import register_routes  # noqa: F401, E402
register_routes(duyurular_bp)
