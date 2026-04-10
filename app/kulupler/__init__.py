from flask import Blueprint

kulupler_bp = Blueprint('kulupler', __name__, template_folder='../templates/kulupler')

from app.kulupler.routes import register_routes  # noqa: F401, E402
register_routes(kulupler_bp)
