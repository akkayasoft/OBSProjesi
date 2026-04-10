import json
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.anket import Anket, AnketSoru
from app.anket.forms import AnketSoruForm

bp = Blueprint('soru', __name__)


@bp.route('/<int:anket_id>/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def yeni(anket_id):
    anket = Anket.query.get_or_404(anket_id)
    form = AnketSoruForm()

    # Varsayilan sira: mevcut soru sayisi + 1
    if not form.sira.data and request.method == 'GET':
        mevcut_sayi = anket.sorular.count()
        form.sira.data = mevcut_sayi + 1

    if form.validate_on_submit():
        secenekler_json = None
        if form.soru_tipi.data == 'coktan_secmeli' and form.secenekler.data:
            secenekler_list = [s.strip() for s in form.secenekler.data.strip().split('\n') if s.strip()]
            secenekler_json = json.dumps(secenekler_list, ensure_ascii=False)

        soru = AnketSoru(
            anket_id=anket.id,
            soru_metni=form.soru_metni.data,
            soru_tipi=form.soru_tipi.data,
            secenekler=secenekler_json,
            sira=form.sira.data or 0,
            zorunlu=form.zorunlu.data,
        )
        db.session.add(soru)
        db.session.commit()
        flash('Soru basariyla eklendi.', 'success')
        return redirect(url_for('anket.yonetim.detay', anket_id=anket.id))

    return render_template('anket/soru_form.html',
                           form=form, anket=anket, baslik='Yeni Soru Ekle')


@bp.route('/<int:soru_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def duzenle(soru_id):
    soru = AnketSoru.query.get_or_404(soru_id)
    anket = soru.anket
    form = AnketSoruForm(obj=soru)

    # Secenekleri textarea formatina cevir
    if request.method == 'GET' and soru.secenekler:
        try:
            secenekler_list = json.loads(soru.secenekler)
            form.secenekler.data = '\n'.join(secenekler_list)
        except (json.JSONDecodeError, TypeError):
            pass

    if form.validate_on_submit():
        soru.soru_metni = form.soru_metni.data
        soru.soru_tipi = form.soru_tipi.data
        soru.sira = form.sira.data or 0
        soru.zorunlu = form.zorunlu.data

        secenekler_json = None
        if form.soru_tipi.data == 'coktan_secmeli' and form.secenekler.data:
            secenekler_list = [s.strip() for s in form.secenekler.data.strip().split('\n') if s.strip()]
            secenekler_json = json.dumps(secenekler_list, ensure_ascii=False)
        soru.secenekler = secenekler_json

        db.session.commit()
        flash('Soru basariyla guncellendi.', 'success')
        return redirect(url_for('anket.yonetim.detay', anket_id=anket.id))

    return render_template('anket/soru_form.html',
                           form=form, anket=anket, baslik='Soruyu Duzenle', soru=soru)


@bp.route('/<int:soru_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def sil(soru_id):
    soru = AnketSoru.query.get_or_404(soru_id)
    anket_id = soru.anket_id
    db.session.delete(soru)
    db.session.commit()
    flash('Soru basariyla silindi.', 'success')
    return redirect(url_for('anket.yonetim.detay', anket_id=anket_id))


@bp.route('/<int:soru_id>/yukari', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def yukari(soru_id):
    soru = AnketSoru.query.get_or_404(soru_id)
    anket = soru.anket
    # Bir ust siradaki soruyu bul
    ust_soru = AnketSoru.query.filter(
        AnketSoru.anket_id == anket.id,
        AnketSoru.sira < soru.sira
    ).order_by(AnketSoru.sira.desc()).first()

    if ust_soru:
        ust_soru.sira, soru.sira = soru.sira, ust_soru.sira
        db.session.commit()
        flash('Soru sirasi guncellendi.', 'success')

    return redirect(url_for('anket.yonetim.detay', anket_id=anket.id))


@bp.route('/<int:soru_id>/asagi', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def asagi(soru_id):
    soru = AnketSoru.query.get_or_404(soru_id)
    anket = soru.anket
    # Bir alt siradaki soruyu bul
    alt_soru = AnketSoru.query.filter(
        AnketSoru.anket_id == anket.id,
        AnketSoru.sira > soru.sira
    ).order_by(AnketSoru.sira.asc()).first()

    if alt_soru:
        alt_soru.sira, soru.sira = soru.sira, alt_soru.sira
        db.session.commit()
        flash('Soru sirasi guncellendi.', 'success')

    return redirect(url_for('anket.yonetim.detay', anket_id=anket.id))
