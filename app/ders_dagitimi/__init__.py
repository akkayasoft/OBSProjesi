from flask import Blueprint

ders_dagitimi_bp = Blueprint('ders_dagitimi', __name__, template_folder='../templates/ders_dagitimi')

from app.ders_dagitimi.routes import register_routes  # noqa: F401, E402
register_routes(ders_dagitimi_bp)
