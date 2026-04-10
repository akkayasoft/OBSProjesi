from flask import Blueprint, render_template
from flask_login import login_required
from app.utils import role_required
from app.extensions import db

bp = Blueprint('akademik_rapor', __name__)


@bp.route('/')
@login_required
@role_required('admin')
def index():
    return render_template('raporlama/akademik_rapor.html')
