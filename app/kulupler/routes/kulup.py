from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required, current_user
from app.extensions import db
from app.models.kulupler import Kulup, KulupUyelik, KulupEtkinlik
from app.models.muhasebe import Personel
from app.kulupler.forms import KulupForm, KulupEtkinlikForm
from datetime import datetime

bp = Blueprint('kulup', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def liste():
    kategori = request.args.get('kategori', '')
    page = request.args.get('page', 1, type=int)

    query = Kulup.query.filter_by(aktif=True)

    if kategori:
        query = query.filter(Kulup.kategori == kategori)

    kulupler = query.order_by(Kulup.ad).paginate(page=page, per_page=12)

    return render_template('kulupler/kulup_listesi.html',
                           kulupler=kulupler,
                           kategori=kategori)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def yeni():
    form = KulupForm()
    personeller = Personel.query.filter_by(aktif=True).order_by(Personel.ad).all()
    form.danisman_id.choices = [(p.id, p.tam_ad) for p in personeller]

    if form.validate_on_submit():
        kulup = Kulup(
            ad=form.ad.data,
            aciklama=form.aciklama.data,
            kategori=form.kategori.data,
            danisman_id=form.danisman_id.data,
            kontenjan=form.kontenjan.data,
            toplanti_gunu=form.toplanti_gunu.data,
            toplanti_saati=form.toplanti_saati.data,
            toplanti_yeri=form.toplanti_yeri.data,
            donem=form.donem.data,
            aktif=form.aktif.data,
        )
        db.session.add(kulup)
        db.session.commit()
        flash('Kulup basariyla olusturuldu.', 'success')
        return redirect(url_for('kulupler.kulup.liste'))

    return render_template('kulupler/kulup_form.html',
                           form=form, baslik='Yeni Kulup')


@bp.route('/<int:kulup_id>')
@login_required
@role_required('admin', 'ogretmen')
def detay(kulup_id):
    kulup = Kulup.query.get_or_404(kulup_id)
    uyeler = KulupUyelik.query.filter_by(
        kulup_id=kulup.id, durum='aktif'
    ).order_by(KulupUyelik.gorev).all()

    etkinlikler = KulupEtkinlik.query.filter_by(
        kulup_id=kulup.id
    ).order_by(KulupEtkinlik.tarih.desc()).limit(10).all()

    return render_template('kulupler/kulup_detay.html',
                           kulup=kulup, uyeler=uyeler,
                           etkinlikler=etkinlikler)


@bp.route('/<int:kulup_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def duzenle(kulup_id):
    kulup = Kulup.query.get_or_404(kulup_id)
    form = KulupForm(obj=kulup)
    personeller = Personel.query.filter_by(aktif=True).order_by(Personel.ad).all()
    form.danisman_id.choices = [(p.id, p.tam_ad) for p in personeller]

    if form.validate_on_submit():
        kulup.ad = form.ad.data
        kulup.aciklama = form.aciklama.data
        kulup.kategori = form.kategori.data
        kulup.danisman_id = form.danisman_id.data
        kulup.kontenjan = form.kontenjan.data
        kulup.toplanti_gunu = form.toplanti_gunu.data
        kulup.toplanti_saati = form.toplanti_saati.data
        kulup.toplanti_yeri = form.toplanti_yeri.data
        kulup.donem = form.donem.data
        kulup.aktif = form.aktif.data
        db.session.commit()
        flash('Kulup basariyla guncellendi.', 'success')
        return redirect(url_for('kulupler.kulup.detay', kulup_id=kulup.id))

    return render_template('kulupler/kulup_form.html',
                           form=form, baslik='Kulup Duzenle')


@bp.route('/<int:kulup_id>/sil', methods=['POST'])
@login_required
@role_required('admin')
def sil(kulup_id):
    kulup = Kulup.query.get_or_404(kulup_id)
    db.session.delete(kulup)
    db.session.commit()
    flash('Kulup basariyla silindi.', 'success')
    return redirect(url_for('kulupler.kulup.liste'))


@bp.route('/<int:kulup_id>/etkinlik/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def etkinlik_yeni(kulup_id):
    kulup = Kulup.query.get_or_404(kulup_id)
    form = KulupEtkinlikForm()

    if form.validate_on_submit():
        etkinlik = KulupEtkinlik(
            kulup_id=kulup.id,
            baslik=form.baslik.data,
            aciklama=form.aciklama.data,
            tarih=form.tarih.data,
            konum=form.konum.data,
            tur=form.tur.data,
            durum=form.durum.data,
            olusturan_id=current_user.id,
        )
        db.session.add(etkinlik)
        db.session.commit()
        flash('Etkinlik basariyla olusturuldu.', 'success')
        return redirect(url_for('kulupler.kulup.detay', kulup_id=kulup.id))

    return render_template('kulupler/etkinlik_form.html',
                           form=form, baslik='Yeni Etkinlik',
                           kulup=kulup)
