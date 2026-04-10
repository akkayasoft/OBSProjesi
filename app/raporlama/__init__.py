from flask import Blueprint

raporlama_bp = Blueprint('raporlama', __name__, template_folder='../templates/raporlama')

from app.raporlama.routes import register_routes  # noqa: F401, E402
register_routes(raporlama_bp)
