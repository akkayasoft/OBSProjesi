from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required, current_user
from app.extensions import db
from app.models.saglik import SaglikTaramasi
from app.models.muhasebe import Ogrenci
from app.saglik.forms import SaglikTaramasiForm

bp = Blueprint('tarama', __name__)


@bp.route('/')
@login_required
@role_required('admin',)
def liste():
    arama = request.args.get('arama', '').strip()
    tur_filtre = request.args.get('tur', '').strip()
    page = request.args.get('page', 1, type=int)

    query = SaglikTaramasi.query.join(Ogrenci)

    if arama:
        query = query.filter(
            db.or_(
                Ogrenci.ad.ilike(f'%{arama}%'),
                Ogrenci.soyad.ilike(f'%{arama}%'),
                Ogrenci.ogrenci_no.ilike(f'%{arama}%'),
            )
        )
    if tur_filtre:
        query = query.filter(SaglikTaramasi.tarama_turu == tur_filtre)

    kayitlar = query.order_by(SaglikTaramasi.tarama_tarihi.desc()).paginate(page=page, per_page=20)

    return render_template('saglik/tarama_listesi.html',
                           kayitlar=kayitlar,
                           arama=arama,
                           tur_filtre=tur_filtre)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin',)
def yeni():
    form = SaglikTaramasiForm()
    form.ogrenci_id.choices = [
        (o.id, f'{o.ogrenci_no} - {o.tam_ad}')
        for o in Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad).all()
    ]

    if form.validate_on_submit():
        kayit = SaglikTaramasi(
            ogrenci_id=form.ogrenci_id.data,
            tarama_tarihi=form.tarama_tarihi.data,
            tarama_turu=form.tarama_turu.data,
            sonuc=form.sonuc.data,
            bulgular=form.bulgular.data,
            oneri=form.oneri.data,
            tarayan_id=current_user.id,
        )
        db.session.add(kayit)
        db.session.commit()
        flash('Sağlık taraması kaydı başarıyla oluşturuldu.', 'success')
        return redirect(url_for('saglik.tarama.liste'))

    return render_template('saglik/tarama_form.html',
                           form=form, baslik='Yeni Sağlık Taraması')


@bp.route('/<int:kayit_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin',)
def duzenle(kayit_id):
    kayit = SaglikTaramasi.query.get_or_404(kayit_id)
    form = SaglikTaramasiForm(obj=kayit)
    form.ogrenci_id.choices = [
        (o.id, f'{o.ogrenci_no} - {o.tam_ad}')
        for o in Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad).all()
    ]

    if form.validate_on_submit():
        kayit.ogrenci_id = form.ogrenci_id.data
        kayit.tarama_tarihi = form.tarama_tarihi.data
        kayit.tarama_turu = form.tarama_turu.data
        kayit.sonuc = form.sonuc.data
        kayit.bulgular = form.bulgular.data
        kayit.oneri = form.oneri.data

        db.session.commit()
        flash('Sağlık taraması kaydı başarıyla güncellendi.', 'success')
        return redirect(url_for('saglik.tarama.liste'))

    return render_template('saglik/tarama_form.html',
                           form=form, baslik='Sağlık Taraması Düzenle')


@bp.route('/<int:kayit_id>')
@login_required
@role_required('admin',)
def detay(kayit_id):
    kayit = SaglikTaramasi.query.get_or_404(kayit_id)
    return render_template('saglik/tarama_detay.html', kayit=kayit)
