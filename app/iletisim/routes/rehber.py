from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required, current_user
from app.extensions import db
from app.models.iletisim import IletisimDefteri
from app.models.muhasebe import Ogrenci
from app.iletisim.forms import IletisimDefteriForm

bp = Blueprint('rehber', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def liste():
    kategori = request.args.get('kategori', '')
    arama = request.args.get('arama', '').strip()
    page = request.args.get('page', 1, type=int)

    query = IletisimDefteri.query.filter_by(aktif=True)

    if kategori:
        query = query.filter(IletisimDefteri.kategori == kategori)
    if arama:
        query = query.filter(
            db.or_(
                IletisimDefteri.ad.ilike(f'%{arama}%'),
                IletisimDefteri.soyad.ilike(f'%{arama}%'),
                IletisimDefteri.telefon.ilike(f'%{arama}%'),
                IletisimDefteri.kurum.ilike(f'%{arama}%'),
            )
        )

    kisiler = query.order_by(
        IletisimDefteri.ad, IletisimDefteri.soyad
    ).paginate(page=page, per_page=20)

    return render_template('iletisim/rehber_listesi.html',
                           kisiler=kisiler, kategori=kategori, arama=arama)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def yeni():
    form = IletisimDefteriForm()

    # Öğrenci listesini doldur
    ogrenciler = Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad, Ogrenci.soyad).all()
    form.ogrenci_id.choices = [(0, 'Seçiniz (isteğe bağlı)')] + [(o.id, f"{o.tam_ad} ({o.sinif})") for o in ogrenciler]

    if form.validate_on_submit():
        kisi = IletisimDefteri(
            ad=form.ad.data,
            soyad=form.soyad.data,
            telefon=form.telefon.data,
            email=form.email.data or None,
            kurum=form.kurum.data or None,
            gorev=form.gorev.data or None,
            kategori=form.kategori.data,
            ogrenci_id=form.ogrenci_id.data if form.ogrenci_id.data else None,
            yakinlik=form.yakinlik.data or None,
            olusturan_id=current_user.id,
        )
        db.session.add(kisi)
        db.session.commit()
        flash('Kişi başarıyla eklendi.', 'success')
        return redirect(url_for('iletisim.rehber.liste'))

    return render_template('iletisim/rehber_form.html', form=form, baslik='Yeni Kişi Ekle')


@bp.route('/<int:kisi_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def duzenle(kisi_id):
    kisi = IletisimDefteri.query.get_or_404(kisi_id)
    form = IletisimDefteriForm(obj=kisi)

    # Öğrenci listesini doldur
    ogrenciler = Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad, Ogrenci.soyad).all()
    form.ogrenci_id.choices = [(0, 'Seçiniz (isteğe bağlı)')] + [(o.id, f"{o.tam_ad} ({o.sinif})") for o in ogrenciler]

    if form.validate_on_submit():
        kisi.ad = form.ad.data
        kisi.soyad = form.soyad.data
        kisi.telefon = form.telefon.data
        kisi.email = form.email.data or None
        kisi.kurum = form.kurum.data or None
        kisi.gorev = form.gorev.data or None
        kisi.kategori = form.kategori.data
        kisi.ogrenci_id = form.ogrenci_id.data if form.ogrenci_id.data else None
        kisi.yakinlik = form.yakinlik.data or None
        db.session.commit()
        flash('Kişi bilgileri güncellendi.', 'success')
        return redirect(url_for('iletisim.rehber.liste'))

    return render_template('iletisim/rehber_form.html', form=form, baslik='Kişi Düzenle')


@bp.route('/<int:kisi_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def sil(kisi_id):
    kisi = IletisimDefteri.query.get_or_404(kisi_id)
    kisi.aktif = False
    db.session.commit()
    flash(f'{kisi.tam_ad} rehberden silindi.', 'success')
    return redirect(url_for('iletisim.rehber.liste'))
