from flask import Blueprint

kayit_bp = Blueprint('kayit', __name__, template_folder='../templates/kayit')

from app.kayit.routes import register_routes  # noqa: F401, E402
register_routes(kayit_bp)
