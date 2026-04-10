from flask import Blueprint

yurt_bp = Blueprint('yurt', __name__, template_folder='../templates/yurt')

from app.yurt.routes import register_routes  # noqa: F401, E402
register_routes(yurt_bp)
