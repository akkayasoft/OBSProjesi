from flask import Blueprint

ayarlar_bp = Blueprint('ayarlar', __name__, template_folder='../templates/ayarlar')

from app.ayarlar.routes import register_routes  # noqa: F401, E402
register_routes(ayarlar_bp)
