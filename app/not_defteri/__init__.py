from flask import Blueprint

not_defteri_bp = Blueprint('not_defteri', __name__, template_folder='../templates/not_defteri')

from app.not_defteri.routes import register_routes  # noqa: F401, E402
register_routes(not_defteri_bp)
