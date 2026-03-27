from flask import Blueprint

devamsizlik_bp = Blueprint('devamsizlik', __name__, template_folder='../templates/devamsizlik')

from app.devamsizlik.routes import register_routes  # noqa: F401, E402
register_routes(devamsizlik_bp)
