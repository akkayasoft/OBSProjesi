from flask import Blueprint

online_sinav_bp = Blueprint('online_sinav', __name__, template_folder='../templates/online_sinav')

from app.online_sinav.routes import register_routes  # noqa: F401, E402
register_routes(online_sinav_bp)
