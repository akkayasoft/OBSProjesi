from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.envanter import Demirbas
from app.models.muhasebe import Personel
from app.envanter.forms import DemirbasForm

bp = Blueprint('demirbas', __name__)


@bp.route('/')
@login_required
@role_required('admin')
def liste():
    page = request.args.get('page', 1, type=int)
    arama = request.args.get('arama', '').strip()
    kategori = request.args.get('kategori', '')
    durum = request.args.get('durum', '')

    query = Demirbas.query
    if arama:
        query = query.filter(
            Demirbas.ad.ilike(f'%{arama}%') | Demirbas.barkod.ilike(f'%{arama}%')
        )
    if kategori:
        query = query.filter(Demirbas.kategori == kategori)
    if durum:
        query = query.filter(Demirbas.durum == durum)

    demirbaslar = query.order_by(Demirbas.ad).paginate(page=page, per_page=20)
    return render_template('envanter/demirbas_listesi.html',
                           demirbaslar=demirbaslar, arama=arama, kategori=kategori, durum=durum)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def yeni():
    form = DemirbasForm()
    personeller = Personel.query.filter_by(aktif=True).order_by(Personel.ad).all()
    form.sorumlu_id.choices = [(0, 'Seciniz')] + [(p.id, f'{p.ad} {p.soyad}') for p in personeller]
    if form.validate_on_submit():
        d = Demirbas(ad=form.ad.data, barkod=form.barkod.data, kategori=form.kategori.data,
                     marka=form.marka.data, model_adi=form.model_adi.data, seri_no=form.seri_no.data,
                     edinme_tarihi=form.edinme_tarihi.data, edinme_fiyati=form.edinme_fiyati.data,
                     konum=form.konum.data, durum=form.durum.data, aciklama=form.aciklama.data,
                     sorumlu_id=form.sorumlu_id.data if form.sorumlu_id.data != 0 else None)
        db.session.add(d)
        db.session.commit()
        flash('Demirbas eklendi.', 'success')
        return redirect(url_for('envanter.demirbas.liste'))
    return render_template('envanter/demirbas_form.html', form=form, baslik='Yeni Demirbas')


@bp.route('/<int:demirbas_id>')
@login_required
@role_required('admin')
def detay(demirbas_id):
    d = Demirbas.query.get_or_404(demirbas_id)
    hareketler = d.hareketler.order_by(db.desc('tarih')).all()
    return render_template('envanter/demirbas_detay.html', demirbas=d, hareketler=hareketler)


@bp.route('/<int:demirbas_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def duzenle(demirbas_id):
    d = Demirbas.query.get_or_404(demirbas_id)
    form = DemirbasForm(obj=d)
    personeller = Personel.query.filter_by(aktif=True).order_by(Personel.ad).all()
    form.sorumlu_id.choices = [(0, 'Seciniz')] + [(p.id, f'{p.ad} {p.soyad}') for p in personeller]
    if form.validate_on_submit():
        d.ad = form.ad.data
        d.barkod = form.barkod.data
        d.kategori = form.kategori.data
        d.marka = form.marka.data
        d.model_adi = form.model_adi.data
        d.seri_no = form.seri_no.data
        d.edinme_tarihi = form.edinme_tarihi.data
        d.edinme_fiyati = form.edinme_fiyati.data
        d.konum = form.konum.data
        d.durum = form.durum.data
        d.aciklama = form.aciklama.data
        d.sorumlu_id = form.sorumlu_id.data if form.sorumlu_id.data != 0 else None
        db.session.commit()
        flash('Demirbas guncellendi.', 'success')
        return redirect(url_for('envanter.demirbas.detay', demirbas_id=d.id))
    return render_template('envanter/demirbas_form.html', form=form, baslik='Demirbas Duzenle')


@bp.route('/<int:demirbas_id>/sil', methods=['POST'])
@login_required
@role_required('admin')
def sil(demirbas_id):
    d = Demirbas.query.get_or_404(demirbas_id)
    db.session.delete(d)
    db.session.commit()
    flash('Demirbas silindi.', 'success')
    return redirect(url_for('envanter.demirbas.liste'))
