from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.saglik import SaglikKaydi, RevirKaydi, AsiTakip, SaglikTaramasi
from app.models.muhasebe import Ogrenci
from app.saglik.forms import SaglikKaydiForm

bp = Blueprint('kayit', __name__)


@bp.route('/')
@login_required
@role_required('admin',)
def liste():
    arama = request.args.get('arama', '').strip()
    page = request.args.get('page', 1, type=int)

    query = SaglikKaydi.query.join(Ogrenci)

    if arama:
        query = query.filter(
            db.or_(
                Ogrenci.ad.ilike(f'%{arama}%'),
                Ogrenci.soyad.ilike(f'%{arama}%'),
                Ogrenci.ogrenci_no.ilike(f'%{arama}%'),
            )
        )

    kayitlar = query.order_by(SaglikKaydi.updated_at.desc()).paginate(page=page, per_page=20)

    return render_template('saglik/kayit_listesi.html',
                           kayitlar=kayitlar,
                           arama=arama)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin',)
def yeni():
    form = SaglikKaydiForm()
    form.ogrenci_id.choices = [
        (o.id, f'{o.ogrenci_no} - {o.tam_ad}')
        for o in Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad).all()
    ]

    if form.validate_on_submit():
        # Ogrenci icin kayit var mi kontrol et
        mevcut = SaglikKaydi.query.filter_by(ogrenci_id=form.ogrenci_id.data).first()
        if mevcut:
            flash('Bu öğrenci için zaten sağlık kaydı bulunmaktadır.', 'warning')
            return redirect(url_for('saglik.kayit.duzenle', kayit_id=mevcut.id))

        kayit = SaglikKaydi(
            ogrenci_id=form.ogrenci_id.data,
            kan_grubu=form.kan_grubu.data or None,
            boy=form.boy.data,
            kilo=form.kilo.data,
            kronik_hastalik=form.kronik_hastalik.data,
            alerji=form.alerji.data,
            surekli_ilac=form.surekli_ilac.data,
            engel_durumu=form.engel_durumu.data,
            ozel_not=form.ozel_not.data,
            acil_kisi_adi=form.acil_kisi_adi.data,
            acil_kisi_telefon=form.acil_kisi_telefon.data,
            acil_kisi_yakinlik=form.acil_kisi_yakinlik.data,
        )
        db.session.add(kayit)
        db.session.commit()
        flash('Sağlık kaydı başarıyla oluşturuldu.', 'success')
        return redirect(url_for('saglik.kayit.liste'))

    return render_template('saglik/kayit_form.html',
                           form=form, baslik='Yeni Sağlık Kaydı')


@bp.route('/<int:kayit_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin',)
def duzenle(kayit_id):
    kayit = SaglikKaydi.query.get_or_404(kayit_id)
    form = SaglikKaydiForm(obj=kayit)
    form.ogrenci_id.choices = [
        (o.id, f'{o.ogrenci_no} - {o.tam_ad}')
        for o in Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad).all()
    ]

    if form.validate_on_submit():
        kayit.kan_grubu = form.kan_grubu.data or None
        kayit.boy = form.boy.data
        kayit.kilo = form.kilo.data
        kayit.kronik_hastalik = form.kronik_hastalik.data
        kayit.alerji = form.alerji.data
        kayit.surekli_ilac = form.surekli_ilac.data
        kayit.engel_durumu = form.engel_durumu.data
        kayit.ozel_not = form.ozel_not.data
        kayit.acil_kisi_adi = form.acil_kisi_adi.data
        kayit.acil_kisi_telefon = form.acil_kisi_telefon.data
        kayit.acil_kisi_yakinlik = form.acil_kisi_yakinlik.data

        db.session.commit()
        flash('Sağlık kaydı başarıyla güncellendi.', 'success')
        return redirect(url_for('saglik.kayit.liste'))

    return render_template('saglik/kayit_form.html',
                           form=form, baslik='Sağlık Kaydı Düzenle')


@bp.route('/<int:kayit_id>/kart')
@login_required
@role_required('admin',)
def saglik_karti(kayit_id):
    kayit = SaglikKaydi.query.get_or_404(kayit_id)
    ogrenci = kayit.ogrenci

    # Ilgili revir, asi, tarama kayitlari
    revir_kayitlari = RevirKaydi.query.filter_by(
        ogrenci_id=ogrenci.id
    ).order_by(RevirKaydi.tarih.desc()).limit(10).all()

    asi_kayitlari = AsiTakip.query.filter_by(
        ogrenci_id=ogrenci.id
    ).order_by(AsiTakip.asi_tarihi.desc()).all()

    tarama_kayitlari = SaglikTaramasi.query.filter_by(
        ogrenci_id=ogrenci.id
    ).order_by(SaglikTaramasi.tarama_tarihi.desc()).all()

    return render_template('saglik/saglik_karti.html',
                           kayit=kayit,
                           ogrenci=ogrenci,
                           revir_kayitlari=revir_kayitlari,
                           asi_kayitlari=asi_kayitlari,
                           tarama_kayitlari=tarama_kayitlari)
