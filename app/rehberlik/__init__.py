from flask import Blueprint

rehberlik_bp = Blueprint('rehberlik', __name__, template_folder='../templates/rehberlik')

from app.rehberlik.routes import register_routes  # noqa: F401, E402
register_routes(rehberlik_bp)
