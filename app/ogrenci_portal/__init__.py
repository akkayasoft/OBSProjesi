from flask import Blueprint

ogrenci_portal_bp = Blueprint('ogrenci_portal', __name__, template_folder='../templates/ogrenci_portal')

from app.ogrenci_portal.routes import register_routes  # noqa: F401, E402
register_routes(ogrenci_portal_bp)
