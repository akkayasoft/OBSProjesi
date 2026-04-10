from flask import Blueprint, render_template
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.muhasebe import Personel

bp = Blueprint('personel_rapor', __name__)


@bp.route('/')
@login_required
@role_required('admin')
def index():
    toplam = Personel.query.filter_by(aktif=True).count()
    pozisyon_dagilim = db.session.query(
        Personel.pozisyon, db.func.count(Personel.id)
    ).filter(Personel.aktif == True).group_by(Personel.pozisyon).all()

    departman_dagilim = db.session.query(
        Personel.departman, db.func.count(Personel.id)
    ).filter(Personel.aktif == True).group_by(Personel.departman).all()

    return render_template('raporlama/personel_rapor.html',
                           toplam=toplam,
                           pozisyon_dagilim=pozisyon_dagilim,
                           departman_dagilim=departman_dagilim)
