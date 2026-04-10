from flask import Blueprint

denetim_bp = Blueprint('denetim', __name__, template_folder='../templates/denetim')

from app.denetim.routes import register_routes  # noqa: F401, E402
register_routes(denetim_bp)
