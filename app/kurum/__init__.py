from flask import Blueprint

kurum_bp = Blueprint('kurum', __name__, template_folder='../templates/kurum')

from app.kurum.routes import register_routes  # noqa: F401, E402
register_routes(kurum_bp)
