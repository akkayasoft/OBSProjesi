from flask import Blueprint

envanter_bp = Blueprint('envanter', __name__, template_folder='../templates/envanter')

from app.envanter.routes import register_routes  # noqa: F401, E402
register_routes(envanter_bp)
