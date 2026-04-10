from flask import Blueprint

kullanici_bp = Blueprint('kullanici', __name__, template_folder='../templates/kullanici')

from app.kullanici.routes import register_routes  # noqa: F401, E402
register_routes(kullanici_bp)
