from flask import Blueprint

karne_bp = Blueprint('karne', __name__, template_folder='../templates/karne')

from app.karne.routes import register_routes  # noqa: F401, E402
register_routes(karne_bp)
