from flask import Blueprint

sinav_oturum_bp = Blueprint('sinav_oturum', __name__, template_folder='../templates/sinav_oturum')

from app.sinav_oturum.routes import register_routes  # noqa: F401, E402
register_routes(sinav_oturum_bp)
