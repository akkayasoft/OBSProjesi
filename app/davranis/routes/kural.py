from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.davranis import DavranisKurali
from app.davranis.forms import DavranisKuraliForm

bp = Blueprint('kural', __name__)


@bp.route('/')
@login_required
@role_required('admin')
def liste():
    kategori = request.args.get('kategori', '')
    tur = request.args.get('tur', '')
    page = request.args.get('page', 1, type=int)

    query = DavranisKurali.query

    if kategori:
        query = query.filter(DavranisKurali.kategori == kategori)
    if tur:
        query = query.filter(DavranisKurali.tur == tur)

    kurallar = query.order_by(
        DavranisKurali.kategori, DavranisKurali.ad
    ).paginate(page=page, per_page=20)

    return render_template('davranis/kural_listesi.html',
                           kurallar=kurallar,
                           kategori=kategori,
                           tur=tur)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def yeni():
    form = DavranisKuraliForm()

    if form.validate_on_submit():
        kural = DavranisKurali(
            ad=form.ad.data,
            kategori=form.kategori.data,
            tur=form.tur.data,
            varsayilan_puan=form.varsayilan_puan.data,
            aciklama=form.aciklama.data,
            aktif=form.aktif.data,
        )
        db.session.add(kural)
        db.session.commit()
        flash('Davranis kurali basariyla olusturuldu.', 'success')
        return redirect(url_for('davranis.kural.liste'))

    return render_template('davranis/kural_form.html',
                           form=form, baslik='Yeni Davranis Kurali')


@bp.route('/<int:kural_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def duzenle(kural_id):
    kural = DavranisKurali.query.get_or_404(kural_id)
    form = DavranisKuraliForm(obj=kural)

    if form.validate_on_submit():
        kural.ad = form.ad.data
        kural.kategori = form.kategori.data
        kural.tur = form.tur.data
        kural.varsayilan_puan = form.varsayilan_puan.data
        kural.aciklama = form.aciklama.data
        kural.aktif = form.aktif.data

        db.session.commit()
        flash('Davranis kurali basariyla guncellendi.', 'success')
        return redirect(url_for('davranis.kural.liste'))

    return render_template('davranis/kural_form.html',
                           form=form, baslik='Davranis Kurali Duzenle')


@bp.route('/<int:kural_id>/sil', methods=['POST'])
@login_required
@role_required('admin')
def sil(kural_id):
    kural = DavranisKurali.query.get_or_404(kural_id)
    db.session.delete(kural)
    db.session.commit()
    flash('Davranis kurali silindi.', 'success')
    return redirect(url_for('davranis.kural.liste'))
