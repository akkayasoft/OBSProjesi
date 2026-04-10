from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.kantin import KantinUrun
from app.kantin.forms import KantinUrunForm

bp = Blueprint('urun', __name__)


@bp.route('/')
@login_required
@role_required('admin')
def liste():
    page = request.args.get('page', 1, type=int)
    kategori = request.args.get('kategori', '')
    query = KantinUrun.query
    if kategori:
        query = query.filter(KantinUrun.kategori == kategori)
    urunler = query.order_by(KantinUrun.ad).paginate(page=page, per_page=20)
    return render_template('kantin/urun_listesi.html', urunler=urunler, kategori=kategori)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def yeni():
    form = KantinUrunForm()
    if form.validate_on_submit():
        urun = KantinUrun(ad=form.ad.data, kategori=form.kategori.data,
                          fiyat=form.fiyat.data, stok=form.stok.data, aktif=form.aktif.data)
        db.session.add(urun)
        db.session.commit()
        flash('Urun eklendi.', 'success')
        return redirect(url_for('kantin.urun.liste'))
    return render_template('kantin/urun_form.html', form=form, baslik='Yeni Urun')


@bp.route('/<int:urun_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def duzenle(urun_id):
    urun = KantinUrun.query.get_or_404(urun_id)
    form = KantinUrunForm(obj=urun)
    if form.validate_on_submit():
        urun.ad = form.ad.data
        urun.kategori = form.kategori.data
        urun.fiyat = form.fiyat.data
        urun.stok = form.stok.data
        urun.aktif = form.aktif.data
        db.session.commit()
        flash('Urun guncellendi.', 'success')
        return redirect(url_for('kantin.urun.liste'))
    return render_template('kantin/urun_form.html', form=form, baslik='Urun Duzenle')


@bp.route('/<int:urun_id>/sil', methods=['POST'])
@login_required
@role_required('admin')
def sil(urun_id):
    urun = KantinUrun.query.get_or_404(urun_id)
    db.session.delete(urun)
    db.session.commit()
    flash('Urun silindi.', 'success')
    return redirect(url_for('kantin.urun.liste'))
