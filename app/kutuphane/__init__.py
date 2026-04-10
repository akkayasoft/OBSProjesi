from flask import Blueprint

kutuphane_bp = Blueprint('kutuphane', __name__, template_folder='../templates/kutuphane')

from app.kutuphane.routes import register_routes  # noqa: F401, E402
register_routes(kutuphane_bp)
