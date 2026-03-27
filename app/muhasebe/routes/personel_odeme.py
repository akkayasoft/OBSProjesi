from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.muhasebe import Personel, PersonelOdemeKaydi, BankaHesabi
from app.muhasebe.forms import PersonelForm, PersonelOdemeForm
from app.muhasebe.utils import banka_hareketi_olustur

bp = Blueprint('personel_odeme', __name__)


@bp.route('/')
@login_required
def liste():
    page = request.args.get('page', 1, type=int)
    personeller = Personel.query.filter_by(aktif=True).order_by(
        Personel.soyad
    ).paginate(page=page, per_page=20, error_out=False)

    return render_template('muhasebe/personel_odeme/liste.html',
                           personeller=personeller)


@bp.route('/personel-ekle', methods=['GET', 'POST'])
@login_required
def personel_ekle():
    form = PersonelForm()
    if form.validate_on_submit():
        personel = Personel(
            sicil_no=form.sicil_no.data,
            ad=form.ad.data,
            soyad=form.soyad.data,
            pozisyon=form.pozisyon.data,
            maas=form.maas.data
        )
        db.session.add(personel)
        db.session.commit()
        flash('Personel başarıyla eklendi.', 'success')
        return redirect(url_for('muhasebe.personel_odeme.liste'))

    return render_template('muhasebe/personel_odeme/personel_form.html',
                           form=form, baslik='Yeni Personel Ekle')


@bp.route('/<int:personel_id>')
@login_required
def detay(personel_id):
    personel = Personel.query.get_or_404(personel_id)
    odemeler = PersonelOdemeKaydi.query.filter_by(
        personel_id=personel_id
    ).order_by(PersonelOdemeKaydi.tarih.desc()).all()

    return render_template('muhasebe/personel_odeme/detay.html',
                           personel=personel, odemeler=odemeler)


@bp.route('/<int:personel_id>/odeme-ekle', methods=['GET', 'POST'])
@login_required
def odeme_ekle(personel_id):
    personel = Personel.query.get_or_404(personel_id)
    form = PersonelOdemeForm()

    hesaplar = BankaHesabi.query.filter_by(aktif=True).all()
    form.banka_hesap_id.choices = [(0, '-- Seçiniz (Opsiyonel) --')] + \
        [(h.id, f'{h.banka_adi} - {h.hesap_adi}') for h in hesaplar]

    if form.validate_on_submit():
        odeme = PersonelOdemeKaydi(
            personel_id=personel_id,
            donem=form.donem.data,
            tutar=form.tutar.data,
            odeme_turu=form.odeme_turu.data,
            banka_hesap_id=form.banka_hesap_id.data if form.banka_hesap_id.data else None,
            aciklama=form.aciklama.data,
            olusturan_id=current_user.id
        )
        db.session.add(odeme)

        if form.banka_hesap_id.data:
            banka_hareketi_olustur(
                form.banka_hesap_id.data, 'cikis', form.tutar.data,
                aciklama=f'Personel maaş: {personel.tam_ad} ({form.donem.data})'
            )

        db.session.commit()
        flash('Personel ödemesi başarıyla kaydedildi.', 'success')
        return redirect(url_for('muhasebe.personel_odeme.detay', personel_id=personel_id))

    return render_template('muhasebe/personel_odeme/odeme_ekle.html',
                           form=form, personel=personel)
