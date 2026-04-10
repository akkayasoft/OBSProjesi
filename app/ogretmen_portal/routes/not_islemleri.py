from flask import Blueprint, render_template, flash
from flask_login import login_required, current_user
from app.utils import role_required
from app.models.muhasebe import Personel
from app.models.not_defteri import Sinav

bp = Blueprint('not_islemleri', __name__)


def get_current_personel():
    return Personel.query.filter_by(
        ad=current_user.ad, soyad=current_user.soyad, aktif=True
    ).first()


@bp.route('/notlar/')
@login_required
@role_required('ogretmen', 'admin')
def index():
    personel = get_current_personel()
    if not personel:
        flash('Personel kaydınız bulunamadı.', 'warning')
        return render_template('ogretmen_portal/notlarim.html',
                               personel=None, sinavlar=[])

    sinavlar = Sinav.query.filter_by(
        ogretmen_id=personel.id, aktif=True
    ).order_by(Sinav.tarih.desc()).all()

    return render_template('ogretmen_portal/notlarim.html',
                           personel=personel, sinavlar=sinavlar)
