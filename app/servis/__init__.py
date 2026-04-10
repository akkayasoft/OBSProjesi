from flask import Blueprint

servis_bp = Blueprint('servis', __name__, template_folder='../templates/servis')

from app.servis.routes import register_routes  # noqa: F401, E402
register_routes(servis_bp)
