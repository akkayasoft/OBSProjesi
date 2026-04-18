from flask import Blueprint

deneme_sinavi_bp = Blueprint(
    'deneme_sinavi', __name__,
    template_folder='../templates/deneme_sinavi',
)

from app.deneme_sinavi.routes import register_routes  # noqa: F401, E402
register_routes(deneme_sinavi_bp)
