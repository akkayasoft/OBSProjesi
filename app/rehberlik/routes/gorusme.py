from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required, current_user
from app.extensions import db
from app.models.rehberlik import Gorusme
from app.models.muhasebe import Ogrenci
from app.rehberlik.forms import GorusmeForm
from app.rehberlik.gorusme_ozet import gorusme_baglam_ozeti

bp = Blueprint('gorusme', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def liste():
    tur = request.args.get('tur', '')
    durum = request.args.get('durum', '')
    arama = request.args.get('arama', '').strip()
    page = request.args.get('page', 1, type=int)

    query = Gorusme.query

    if tur:
        query = query.filter(Gorusme.gorusme_turu == tur)
    if durum:
        query = query.filter(Gorusme.durum == durum)
    if arama:
        query = query.filter(
            db.or_(
                Gorusme.konu.ilike(f'%{arama}%'),
                Gorusme.icerik.ilike(f'%{arama}%')
            )
        )

    gorusmeler = query.order_by(
        Gorusme.gorusme_tarihi.desc()
    ).paginate(page=page, per_page=20)

    return render_template('rehberlik/gorusme_listesi.html',
                           gorusmeler=gorusmeler,
                           tur=tur,
                           durum=durum,
                           arama=arama)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def yeni():
    form = GorusmeForm()
    form.ogrenci_id.choices = [(o.id, f'{o.ogrenci_no} - {o.tam_ad}')
                                for o in Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad).all()]

    # Pre-select ogrenci varsa (querystring'den geliyorsa) baglam ozetini yukle
    secili_ogrenci_id = request.args.get('ogrenci_id', type=int)
    if secili_ogrenci_id and not form.ogrenci_id.data:
        form.ogrenci_id.data = secili_ogrenci_id
    baglam = None
    if secili_ogrenci_id:
        baglam = gorusme_baglam_ozeti(secili_ogrenci_id)
        if baglam.get('ogrenci') is None:
            baglam = None

    if form.validate_on_submit():
        gorusme = Gorusme(
            ogrenci_id=form.ogrenci_id.data,
            rehber_id=current_user.id,
            gorusme_tarihi=form.gorusme_tarihi.data,
            gorusme_turu=form.gorusme_turu.data,
            konu=form.konu.data,
            icerik=form.icerik.data,
            sonuc_ve_oneri=form.sonuc_ve_oneri.data,
            gizlilik_seviyesi=form.gizlilik_seviyesi.data,
            durum=form.durum.data,
        )
        db.session.add(gorusme)
        db.session.commit()
        flash('Gorusme basariyla olusturuldu.', 'success')
        return redirect(url_for('rehberlik.gorusme.liste'))

    return render_template('rehberlik/gorusme_form.html',
                           form=form, baslik='Yeni Gorusme',
                           baglam=baglam)


@bp.route('/<int:gorusme_id>')
@login_required
@role_required('admin', 'ogretmen')
def detay(gorusme_id):
    gorusme = Gorusme.query.get_or_404(gorusme_id)
    return render_template('rehberlik/gorusme_detay.html', gorusme=gorusme)


@bp.route('/<int:gorusme_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def duzenle(gorusme_id):
    gorusme = Gorusme.query.get_or_404(gorusme_id)
    form = GorusmeForm(obj=gorusme)
    form.ogrenci_id.choices = [(o.id, f'{o.ogrenci_no} - {o.tam_ad}')
                                for o in Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad).all()]

    if form.validate_on_submit():
        gorusme.ogrenci_id = form.ogrenci_id.data
        gorusme.gorusme_tarihi = form.gorusme_tarihi.data
        gorusme.gorusme_turu = form.gorusme_turu.data
        gorusme.konu = form.konu.data
        gorusme.icerik = form.icerik.data
        gorusme.sonuc_ve_oneri = form.sonuc_ve_oneri.data
        gorusme.gizlilik_seviyesi = form.gizlilik_seviyesi.data
        gorusme.durum = form.durum.data

        db.session.commit()
        flash('Gorusme basariyla guncellendi.', 'success')
        return redirect(url_for('rehberlik.gorusme.detay', gorusme_id=gorusme.id))

    return render_template('rehberlik/gorusme_form.html',
                           form=form, baslik='Gorusme Duzenle')


@bp.route('/<int:gorusme_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def sil(gorusme_id):
    gorusme = Gorusme.query.get_or_404(gorusme_id)
    konu = gorusme.konu
    db.session.delete(gorusme)
    db.session.commit()
    flash(f'"{konu}" gorusmesi silindi.', 'success')
    return redirect(url_for('rehberlik.gorusme.liste'))
