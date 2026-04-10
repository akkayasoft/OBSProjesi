from flask import Blueprint

belge_bp = Blueprint('belge', __name__, template_folder='../templates/belge')

from app.belge.routes import register_routes  # noqa: F401, E402
register_routes(belge_bp)
