from flask import Blueprint

personel_bp = Blueprint('personel', __name__, template_folder='../templates/personel')

from app.personel.routes import register_routes  # noqa: F401, E402
register_routes(personel_bp)
