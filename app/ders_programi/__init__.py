from flask import Blueprint

ders_programi_bp = Blueprint('ders_programi', __name__, template_folder='../templates/ders_programi')

from app.ders_programi.routes import register_routes  # noqa: F401, E402
register_routes(ders_programi_bp)
