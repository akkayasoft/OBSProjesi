from flask import Blueprint, render_template, flash
from flask_login import login_required, current_user
from app.utils import role_required
from app.models.muhasebe import Personel
from app.models.ders_dagitimi import DersProgrami

bp = Blueprint('ders_programi', __name__)

GUNLER = ['Pazartesi', 'Sali', 'Carsamba', 'Persembe', 'Cuma']
SAATLER = list(range(1, 9))


def get_current_personel():
    return Personel.query.filter_by(
        ad=current_user.ad, soyad=current_user.soyad, aktif=True
    ).first()


@bp.route('/program/')
@login_required
@role_required('ogretmen', 'admin')
def index():
    personel = get_current_personel()
    if not personel:
        flash('Personel kaydınız bulunamadı.', 'warning')
        return render_template('ogretmen_portal/program.html',
                               personel=None, program={},
                               gunler=GUNLER, saatler=SAATLER)

    # Haftalik program grid olustur
    dersler = DersProgrami.query.filter_by(
        ogretmen_id=personel.id, aktif=True
    ).all()

    program = {}
    for gun in GUNLER:
        program[gun] = {}
        for saat in SAATLER:
            program[gun][saat] = None

    for d in dersler:
        if d.gun in program and d.ders_saati in program.get(d.gun, {}):
            program[d.gun][d.ders_saati] = d

    return render_template('ogretmen_portal/program.html',
                           personel=personel, program=program,
                           gunler=GUNLER, saatler=SAATLER)
