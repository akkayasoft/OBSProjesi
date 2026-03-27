from flask import Blueprint

muhasebe_bp = Blueprint('muhasebe', __name__, template_folder='../templates/muhasebe')

from app.muhasebe.routes import register_routes  # noqa: F401, E402
register_routes(muhasebe_bp)
