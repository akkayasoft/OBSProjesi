from flask import Blueprint, render_template, flash
from flask_login import login_required, current_user
from app.utils import role_required
from app.models.muhasebe import Personel
from app.models.ders_dagitimi import DersProgrami
from app.models.not_defteri import Sinav
from app.models.duyurular import Duyuru
from app.extensions import db
from datetime import date, datetime

bp = Blueprint('dashboard', __name__)

GUNLER = ['Pazartesi', 'Sali', 'Carsamba', 'Persembe', 'Cuma']
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


@bp.route('/')
@login_required
@role_required('ogretmen', 'admin')
def index():
    personel = get_current_personel()
    if not personel:
        flash('Personel kaydınız bulunamadı.', 'warning')
        return render_template('ogretmen_portal/index.html',
                               personel=None,
                               bugunun_dersleri=[],
                               sinav_sayisi=0,
                               sinif_sayisi=0,
                               ders_sayisi=0,
                               duyurular=[])

    bugun = date.today()
    bugunun_gunu = GUN_MAP.get(bugun.weekday(), '')

    # Bugunun dersleri
    bugunun_dersleri = DersProgrami.query.filter_by(
        ogretmen_id=personel.id, gun=bugunun_gunu, aktif=True
    ).order_by(DersProgrami.ders_saati.asc()).all()

    # Istatistikler
    sinav_sayisi = Sinav.query.filter_by(
        ogretmen_id=personel.id, aktif=True
    ).count()

    sinif_ids = db.session.query(DersProgrami.sube_id).filter_by(
        ogretmen_id=personel.id, aktif=True
    ).distinct().all()
    sinif_sayisi = len(sinif_ids)

    ders_ids = db.session.query(DersProgrami.ders_id).filter_by(
        ogretmen_id=personel.id, aktif=True
    ).distinct().all()
    ders_sayisi = len(ders_ids)

    # Son duyurular
    duyurular = Duyuru.query.filter(
        Duyuru.aktif == True,  # noqa: E712
        db.or_(
            Duyuru.hedef_kitle == 'tumu',
            Duyuru.hedef_kitle == 'ogretmenler'
        )
    ).order_by(Duyuru.yayinlanma_tarihi.desc()).limit(5).all()

    return render_template('ogretmen_portal/index.html',
                           personel=personel,
                           bugunun_dersleri=bugunun_dersleri,
                           sinav_sayisi=sinav_sayisi,
                           sinif_sayisi=sinif_sayisi,
                           ders_sayisi=ders_sayisi,
                           duyurular=duyurular)
