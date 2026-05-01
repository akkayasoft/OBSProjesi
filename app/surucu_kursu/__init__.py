from flask import Blueprint

surucu_kursu_bp = Blueprint(
    'surucu_kursu', __name__,
    template_folder='../templates/surucu_kursu',
)

from app.surucu_kursu import routes  # noqa: F401, E402
