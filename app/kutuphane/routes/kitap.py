from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.kutuphane import Kitap
from app.kutuphane.forms import KitapForm

bp = Blueprint('kitap', __name__)


@bp.route('/')
@login_required
@role_required('admin')
def liste():
    page = request.args.get('page', 1, type=int)
    arama = request.args.get('arama', '').strip()
    kategori = request.args.get('kategori', '')

    query = Kitap.query
    if arama:
        query = query.filter(
            Kitap.baslik.ilike(f'%{arama}%') |
            Kitap.yazar.ilike(f'%{arama}%') |
            Kitap.isbn.ilike(f'%{arama}%')
        )
    if kategori:
        query = query.filter(Kitap.kategori == kategori)

    kitaplar = query.order_by(Kitap.baslik).paginate(page=page, per_page=20)
    return render_template('kutuphane/kitap_listesi.html',
                           kitaplar=kitaplar, arama=arama, kategori=kategori)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def yeni():
    form = KitapForm()
    if form.validate_on_submit():
        kitap = Kitap(baslik=form.baslik.data, yazar=form.yazar.data,
                      isbn=form.isbn.data, yayinevi=form.yayinevi.data,
                      yayin_yili=form.yayin_yili.data, kategori=form.kategori.data,
                      raf_no=form.raf_no.data, adet=form.adet.data,
                      mevcut_adet=form.adet.data, aciklama=form.aciklama.data)
        db.session.add(kitap)
        db.session.commit()
        flash('Kitap eklendi.', 'success')
        return redirect(url_for('kutuphane.kitap.liste'))
    return render_template('kutuphane/kitap_form.html', form=form, baslik='Yeni Kitap')


@bp.route('/<int:kitap_id>')
@login_required
@role_required('admin')
def detay(kitap_id):
    kitap = Kitap.query.get_or_404(kitap_id)
    odunc_kayitlari = kitap.odunc_kayitlari.order_by(db.desc('odunc_tarihi')).all()
    return render_template('kutuphane/kitap_detay.html',
                           kitap=kitap, odunc_kayitlari=odunc_kayitlari)


@bp.route('/<int:kitap_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def duzenle(kitap_id):
    kitap = Kitap.query.get_or_404(kitap_id)
    form = KitapForm(obj=kitap)
    if form.validate_on_submit():
        fark = form.adet.data - kitap.adet
        kitap.baslik = form.baslik.data
        kitap.yazar = form.yazar.data
        kitap.isbn = form.isbn.data
        kitap.yayinevi = form.yayinevi.data
        kitap.yayin_yili = form.yayin_yili.data
        kitap.kategori = form.kategori.data
        kitap.raf_no = form.raf_no.data
        kitap.adet = form.adet.data
        kitap.mevcut_adet = max(0, kitap.mevcut_adet + fark)
        kitap.aciklama = form.aciklama.data
        db.session.commit()
        flash('Kitap guncellendi.', 'success')
        return redirect(url_for('kutuphane.kitap.detay', kitap_id=kitap.id))
    return render_template('kutuphane/kitap_form.html', form=form, baslik='Kitap Duzenle')


@bp.route('/<int:kitap_id>/sil', methods=['POST'])
@login_required
@role_required('admin')
def sil(kitap_id):
    kitap = Kitap.query.get_or_404(kitap_id)
    db.session.delete(kitap)
    db.session.commit()
    flash('Kitap silindi.', 'success')
    return redirect(url_for('kutuphane.kitap.liste'))
