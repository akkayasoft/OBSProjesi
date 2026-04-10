from flask import Blueprint, render_template, flash
from flask_login import login_required, current_user
from app.utils import role_required
from app.models.duyurular import Duyuru
from app.extensions import db

bp = Blueprint('duyurular_portal', __name__)


@bp.route('/duyurular/')
@login_required
@role_required('ogrenci', 'veli', 'admin')
def index():
    duyurular = Duyuru.query.filter(
        Duyuru.aktif == True,  # noqa: E712
        db.or_(
            Duyuru.hedef_kitle == 'tumu',
            Duyuru.hedef_kitle == 'ogrenciler',
            Duyuru.hedef_kitle == 'veliler'
        )
    ).order_by(Duyuru.sabitlenmis.desc(), Duyuru.yayinlanma_tarihi.desc()).all()

    return render_template('ogrenci_portal/duyurular.html', duyurular=duyurular)
