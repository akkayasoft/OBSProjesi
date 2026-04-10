from flask import Blueprint, render_template, flash, abort
from flask_login import login_required, current_user
from app.utils import role_required
from app.models.muhasebe import Personel
from app.models.ders_dagitimi import DersProgrami
from app.models.kayit import Sube, OgrenciKayit
from app.extensions import db

bp = Blueprint('siniflarim', __name__)


def get_current_personel():
    return Personel.query.filter_by(
        ad=current_user.ad, soyad=current_user.soyad, aktif=True
    ).first()


@bp.route('/siniflarim/')
@login_required
@role_required('ogretmen', 'admin')
def index():
    personel = get_current_personel()
    if not personel:
        flash('Personel kaydınız bulunamadı.', 'warning')
        return render_template('ogretmen_portal/siniflarim.html',
                               personel=None, siniflar=[])

    # Ogretmenin ders verdigi subeler
    sube_ids = db.session.query(DersProgrami.sube_id).filter_by(
        ogretmen_id=personel.id, aktif=True
    ).distinct().all()
    sube_ids = [s[0] for s in sube_ids]

    siniflar = Sube.query.filter(Sube.id.in_(sube_ids)).all() if sube_ids else []

    return render_template('ogretmen_portal/siniflarim.html',
                           personel=personel, siniflar=siniflar)


@bp.route('/siniflarim/<int:sube_id>')
@login_required
@role_required('ogretmen', 'admin')
def sinif_detay(sube_id):
    personel = get_current_personel()
    if not personel:
        flash('Personel kaydınız bulunamadı.', 'warning')
        return render_template('ogretmen_portal/sinif_ogrencileri.html',
                               personel=None, sube=None, ogrenciler=[])

    # Bu subeye ders veriyor mu kontrol
    atama = DersProgrami.query.filter_by(
        ogretmen_id=personel.id, sube_id=sube_id, aktif=True
    ).first()
    if not atama:
        abort(403)

    sube = Sube.query.get_or_404(sube_id)
    kayitlar = OgrenciKayit.query.filter_by(
        sube_id=sube_id, durum='aktif'
    ).all()
    ogrenciler = [k.ogrenci for k in kayitlar]

    return render_template('ogretmen_portal/sinif_ogrencileri.html',
                           personel=personel, sube=sube, ogrenciler=ogrenciler)
