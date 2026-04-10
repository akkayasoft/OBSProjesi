from flask import Blueprint

bildirim_bp = Blueprint('bildirim', __name__, template_folder='../templates/bildirim')

from app.bildirim import routes  # noqa: F401, E402
