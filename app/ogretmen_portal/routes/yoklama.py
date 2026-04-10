from flask import Blueprint, render_template, flash
from flask_login import login_required, current_user
from app.utils import role_required
from app.models.muhasebe import Personel
from app.models.ders_dagitimi import DersProgrami
from datetime import date

bp = Blueprint('yoklama', __name__)

GUN_MAP = {
    0: 'Pazartesi',
    1: 'Sali',
    2: 'Carsamba',
    3: 'Persembe',
    4: 'Cuma',
    5: 'Cumartesi',
    6: 'Pazar',
}


def get_current_personel():
    return Personel.query.filter_by(
        ad=current_user.ad, soyad=current_user.soyad, aktif=True
    ).first()


@bp.route('/yoklama/')
@login_required
@role_required('ogretmen', 'admin')
def index():
    personel = get_current_personel()
    if not personel:
        flash('Personel kaydınız bulunamadı.', 'warning')
        return render_template('ogretmen_portal/yoklama.html',
                               personel=None, bugunun_dersleri=[],
                               bugun=date.today())

    bugun = date.today()
    bugunun_gunu = GUN_MAP.get(bugun.weekday(), '')

    bugunun_dersleri = DersProgrami.query.filter_by(
        ogretmen_id=personel.id, gun=bugunun_gunu, aktif=True
    ).order_by(DersProgrami.ders_saati.asc()).all()

    return render_template('ogretmen_portal/yoklama.html',
                           personel=personel,
                           bugunun_dersleri=bugunun_dersleri,
                           bugun=bugun)
