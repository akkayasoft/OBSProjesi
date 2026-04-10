from flask import Blueprint

anket_bp = Blueprint('anket', __name__, template_folder='../templates/anket')

from app.anket.routes import register_routes  # noqa: F401, E402
register_routes(anket_bp)
