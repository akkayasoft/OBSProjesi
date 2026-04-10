from flask import Blueprint

iletisim_bp = Blueprint('iletisim', __name__, template_folder='../templates/iletisim')

from app.iletisim.routes import register_routes  # noqa: F401, E402
register_routes(iletisim_bp)
