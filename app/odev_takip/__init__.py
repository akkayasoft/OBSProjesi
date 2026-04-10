from flask import Blueprint

odev_takip_bp = Blueprint('odev_takip', __name__, template_folder='../templates/odev_takip')

from app.odev_takip.routes import register_routes  # noqa: F401, E402
register_routes(odev_takip_bp)
