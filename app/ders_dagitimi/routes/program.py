from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.ders_dagitimi import Ders, DersProgrami
from app.models.muhasebe import Personel
from app.models.kayit import Sinif, Sube
from app.ders_dagitimi.forms import DersProgramiForm

bp = Blueprint('program', __name__)

GUNLER = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma']
SAATLER = list(range(1, 9))


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def liste():
    sube_id = request.args.get('sube_id', type=int)
    donem = request.args.get('donem', '2025-2026')

    subeler = Sube.query.join(Sube.sinif).filter(Sube.aktif == True).order_by(Sinif.seviye, Sube.ad).all()

    # Varsayılan olarak ilk şubeyi seç
    if not sube_id and subeler:
        sube_id = subeler[0].id

    program = {}
    secili_sube = None

    if sube_id:
        secili_sube = Sube.query.get(sube_id)
        kayitlar = DersProgrami.query.filter_by(
            sube_id=sube_id, donem=donem, aktif=True
        ).all()

        for kayit in kayitlar:
            key = (kayit.gun, kayit.ders_saati)
            program[key] = kayit

    return render_template('ders_dagitimi/program.html',
                           program=program,
                           gunler=GUNLER,
                           saatler=SAATLER,
                           subeler=subeler,
                           sube_id=sube_id,
                           secili_sube=secili_sube,
                           donem=donem)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def yeni():
    form = DersProgramiForm()

    # Seçenekleri doldur
    form.ders_id.choices = [(d.id, f'{d.kod} - {d.ad}') for d in Ders.query.filter_by(aktif=True).order_by(Ders.ad).all()]
    form.ogretmen_id.choices = [(p.id, f'{p.tam_ad} ({p.sicil_no})') for p in Personel.query.filter_by(aktif=True).order_by(Personel.ad).all()]
    form.sube_id.choices = [(s.id, s.tam_ad) for s in Sube.query.join(Sube.sinif).filter(Sube.aktif == True).order_by(Sinif.seviye, Sube.ad).all()]

    if form.validate_on_submit():
        # Çakışma kontrolü
        mevcut = DersProgrami.query.filter_by(
            sube_id=form.sube_id.data,
            gun=form.gun.data,
            ders_saati=form.ders_saati.data,
            donem=form.donem.data,
        ).first()
        if mevcut:
            flash('Bu sınıf/şube için bu gün ve saatte zaten bir ders var!', 'danger')
            return render_template('ders_dagitimi/program_form.html',
                                   form=form, baslik='Yeni Program Kaydı')

        # Öğretmen çakışma kontrolü
        ogretmen_cakisma = DersProgrami.query.filter_by(
            ogretmen_id=form.ogretmen_id.data,
            gun=form.gun.data,
            ders_saati=form.ders_saati.data,
            donem=form.donem.data,
            aktif=True,
        ).first()
        if ogretmen_cakisma:
            flash('Bu öğretmenin bu gün ve saatte başka bir dersi var!', 'danger')
            return render_template('ders_dagitimi/program_form.html',
                                   form=form, baslik='Yeni Program Kaydı')

        kayit = DersProgrami(
            ders_id=form.ders_id.data,
            ogretmen_id=form.ogretmen_id.data,
            sube_id=form.sube_id.data,
            gun=form.gun.data,
            ders_saati=form.ders_saati.data,
            donem=form.donem.data,
            derslik=form.derslik.data or None,
        )
        db.session.add(kayit)
        db.session.commit()
        flash('Program kaydı başarıyla eklendi.', 'success')
        return redirect(url_for('ders_dagitimi.program.liste', sube_id=form.sube_id.data))

    return render_template('ders_dagitimi/program_form.html',
                           form=form, baslik='Yeni Program Kaydı')


@bp.route('/<int:program_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def sil(program_id):
    kayit = DersProgrami.query.get_or_404(program_id)
    sube_id = kayit.sube_id
    db.session.delete(kayit)
    db.session.commit()
    flash('Program kaydı silindi.', 'success')
    return redirect(url_for('ders_dagitimi.program.liste', sube_id=sube_id))
