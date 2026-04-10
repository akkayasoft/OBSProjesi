from flask import Blueprint, render_template, flash
from flask_login import login_required, current_user
from app.utils import role_required
from app.models.muhasebe import Ogrenci
from app.models.kayit import OgrenciKayit
from app.models.ders_dagitimi import DersProgrami
from app.extensions import db

bp = Blueprint('program', __name__)

GUNLER = ['Pazartesi', 'Sali', 'Carsamba', 'Persembe', 'Cuma']
SAATLER = list(range(1, 9))


def get_current_ogrenci():
    if current_user.rol == 'veli':
        return Ogrenci.query.filter_by(soyad=current_user.soyad, aktif=True).first()
    return Ogrenci.query.filter_by(ad=current_user.ad, soyad=current_user.soyad, aktif=True).first()


@bp.route('/program/')
@login_required
@role_required('ogrenci', 'veli', 'admin')
def index():
    ogrenci = get_current_ogrenci()
    if not ogrenci:
        flash('Ogrenci kaydiniz bulunamadi.', 'warning')
        return render_template('ogrenci_portal/program.html',
                               ogrenci=None, program={}, gunler=GUNLER, saatler=SAATLER)

    # Ogrencinin subesini bul
    kayit = OgrenciKayit.query.filter_by(
        ogrenci_id=ogrenci.id, durum='aktif'
    ).first()

    program = {}
    if kayit:
        dersler = DersProgrami.query.filter_by(
            sube_id=kayit.sube_id, aktif=True
        ).all()

        for d in dersler:
            if d.gun not in program:
                program[d.gun] = {}
            program[d.gun][d.ders_saati] = d

    return render_template('ogrenci_portal/program.html',
                           ogrenci=ogrenci, program=program,
                           gunler=GUNLER, saatler=SAATLER)
