from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.ders_dagitimi import Ders
from app.ders_dagitimi.forms import DersForm

bp = Blueprint('ders', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def liste():
    arama = request.args.get('arama', '')
    kategori = request.args.get('kategori', '')
    seviye = request.args.get('seviye', '', type=str)
    page = request.args.get('page', 1, type=int)

    query = Ders.query

    if arama:
        query = query.filter(
            db.or_(
                Ders.ad.ilike(f'%{arama}%'),
                Ders.kod.ilike(f'%{arama}%'),
            )
        )

    if kategori:
        query = query.filter(Ders.kategori == kategori)

    if seviye:
        query = query.filter(Ders.sinif_seviyesi == int(seviye))

    dersler = query.order_by(Ders.kod).paginate(page=page, per_page=20)

    return render_template('ders_dagitimi/ders_listesi.html',
                           dersler=dersler,
                           arama=arama,
                           kategori=kategori,
                           seviye=seviye)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def yeni():
    form = DersForm()

    if form.validate_on_submit():
        mevcut = Ders.query.filter_by(kod=form.kod.data).first()
        if mevcut:
            flash('Bu ders kodu zaten kayıtlı!', 'danger')
            return render_template('ders_dagitimi/ders_form.html',
                                   form=form, baslik='Yeni Ders')

        ders = Ders(
            kod=form.kod.data,
            ad=form.ad.data,
            kategori=form.kategori.data,
            haftalik_saat=form.haftalik_saat.data,
            sinif_seviyesi=form.sinif_seviyesi.data,
            aciklama=form.aciklama.data or None,
        )
        db.session.add(ders)
        db.session.commit()
        flash(f'{ders.ad} dersi başarıyla eklendi.', 'success')
        return redirect(url_for('ders_dagitimi.ders.liste'))

    return render_template('ders_dagitimi/ders_form.html',
                           form=form, baslik='Yeni Ders')


@bp.route('/<int:ders_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def duzenle(ders_id):
    ders = Ders.query.get_or_404(ders_id)
    form = DersForm(obj=ders)

    if form.validate_on_submit():
        if form.kod.data != ders.kod:
            mevcut = Ders.query.filter_by(kod=form.kod.data).first()
            if mevcut:
                flash('Bu ders kodu zaten kayıtlı!', 'danger')
                return render_template('ders_dagitimi/ders_form.html',
                                       form=form, baslik='Ders Düzenle')

        ders.kod = form.kod.data
        ders.ad = form.ad.data
        ders.kategori = form.kategori.data
        ders.haftalik_saat = form.haftalik_saat.data
        ders.sinif_seviyesi = form.sinif_seviyesi.data
        ders.aciklama = form.aciklama.data or None

        db.session.commit()
        flash('Ders bilgileri güncellendi.', 'success')
        return redirect(url_for('ders_dagitimi.ders.liste'))

    return render_template('ders_dagitimi/ders_form.html',
                           form=form, baslik='Ders Düzenle')


@bp.route('/<int:ders_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def sil(ders_id):
    ders = Ders.query.get_or_404(ders_id)

    # Bağlı program kaydı var mı kontrol et
    if ders.programlar.count() > 0:
        flash('Bu derse ait program kayıtları var, önce onları siliniz.', 'danger')
        return redirect(url_for('ders_dagitimi.ders.liste'))

    if ders.atamalar.count() > 0:
        flash('Bu derse ait öğretmen atamaları var, önce onları siliniz.', 'danger')
        return redirect(url_for('ders_dagitimi.ders.liste'))

    ad = ders.ad
    db.session.delete(ders)
    db.session.commit()
    flash(f'{ad} dersi silindi.', 'success')
    return redirect(url_for('ders_dagitimi.ders.liste'))
