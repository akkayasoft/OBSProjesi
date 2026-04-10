from flask import Blueprint

ogretmen_portal_bp = Blueprint('ogretmen_portal', __name__, template_folder='../templates/ogretmen_portal')

from app.ogretmen_portal.routes import register_routes  # noqa: F401, E402
register_routes(ogretmen_portal_bp)
