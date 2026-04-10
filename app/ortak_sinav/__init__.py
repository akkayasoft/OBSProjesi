from flask import Blueprint

ortak_sinav_bp = Blueprint('ortak_sinav', __name__, template_folder='../templates/ortak_sinav')

from app.ortak_sinav.routes import register_routes  # noqa: F401, E402
register_routes(ortak_sinav_bp)
