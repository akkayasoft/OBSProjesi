"""Surucu kursu modulu route'lari.

Sadece kurum_tipi='surucu_kursu' tenant'larinda menude gorunur,
ama URL'ler her tenant'ta calisir (yetkili kullanici varsa). Mevcut
OBS'i etkilememek icin /surucu-kursu/ prefix'i kullanilir.
"""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import (render_template, redirect, url_for, flash, request,
                   abort, g)
from flask_login import login_required, current_user
from sqlalchemy import or_, func

from app.extensions import db
from app.surucu_kursu import surucu_kursu_bp
from app.models.user import User
from app.models.surucu_kursu import (
    Kursiyer, EHLIYET_SINIFLARI, EHLIYET_SINIF_DICT,
)


def _surucu_kursu_tenant_required():
    """Tenant kurum_tipi 'surucu_kursu' degilse 404. Bu blueprint sadece
    surucu kursu tenant'larinda kullanilmali."""
    tenant = getattr(g, 'tenant', None)
    if tenant is None or getattr(tenant, 'kurum_tipi', 'dershane') != 'surucu_kursu':
        abort(404)


def _decimal_or_none(s):
    if s is None or s == '':
        return None
    try:
        return Decimal(str(s).replace(',', '.'))
    except (InvalidOperation, ValueError):
        return None


def _int_or_none(s):
    if s is None or s == '':
        return None
    try:
        return int(s)
    except (ValueError, TypeError):
        return None


def _date_or_none(s):
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


# === Kursiyer liste ===

@surucu_kursu_bp.route('/kursiyer/')
@login_required
def kursiyer_liste():
    _surucu_kursu_tenant_required()
    arama = (request.args.get('arama') or '').strip()
    sinif = (request.args.get('sinif') or '').strip()
    durum = (request.args.get('durum') or 'aktif').strip()

    q = Kursiyer.query
    if durum == 'aktif':
        q = q.filter(Kursiyer.aktif.is_(True))
    elif durum == 'pasif':
        q = q.filter(Kursiyer.aktif.is_(False))

    if sinif and sinif in EHLIYET_SINIF_DICT:
        q = q.filter(Kursiyer.ehliyet_sinifi == sinif)

    if arama:
        like = f'%{arama}%'
        q = q.filter(or_(
            Kursiyer.ad.ilike(like),
            Kursiyer.soyad.ilike(like),
            Kursiyer.telefon.ilike(like),
        ))

    kursiyerler = q.order_by(Kursiyer.id.desc()).all()
    toplam = Kursiyer.query.filter(Kursiyer.aktif.is_(True)).count()

    return render_template(
        'surucu_kursu/kursiyer_liste.html',
        kursiyerler=kursiyerler,
        ehliyet_siniflari=EHLIYET_SINIFLARI,
        ehliyet_dict=EHLIYET_SINIF_DICT,
        arama=arama, sinif=sinif, durum=durum,
        toplam_aktif=toplam,
    )


# === Kursiyer yeni ===

@surucu_kursu_bp.route('/kursiyer/yeni', methods=['GET', 'POST'])
@login_required
def kursiyer_yeni():
    _surucu_kursu_tenant_required()

    egitmenler = User.query.filter(
        User.aktif.is_(True),
        User.rol.in_(['admin', 'yonetici', 'ogretmen']),
    ).order_by(User.ad, User.soyad).all()

    form_data = {
        'ad': '', 'soyad': '', 'telefon': '',
        'kayit_tarihi': date.today().isoformat(),
        'ehliyet_sinifi': '',
        'ders_sayisi': '',
        'fiyat': '',
        'egitmen_id': '',
        'notlar': '',
    }
    hata = None

    if request.method == 'POST':
        for k in form_data:
            form_data[k] = (request.form.get(k) or '').strip()

        ad = form_data['ad']
        soyad = form_data['soyad']
        ehliyet_sinifi = form_data['ehliyet_sinifi']
        kayit_tarihi = _date_or_none(form_data['kayit_tarihi']) or date.today()

        if not ad or not soyad:
            hata = 'Ad ve soyad zorunludur.'
        elif ehliyet_sinifi not in EHLIYET_SINIF_DICT:
            hata = 'Geçerli bir ehliyet sınıfı seçin.'

        if hata:
            return render_template(
                'surucu_kursu/kursiyer_form.html',
                hata=hata, form=form_data,
                ehliyet_siniflari=EHLIYET_SINIFLARI,
                egitmenler=egitmenler, baslik='Yeni Kursiyer',
            )

        k = Kursiyer(
            ad=ad, soyad=soyad,
            telefon=form_data['telefon'] or None,
            kayit_tarihi=kayit_tarihi,
            ehliyet_sinifi=ehliyet_sinifi,
            ders_sayisi=_int_or_none(form_data['ders_sayisi']),
            fiyat=_decimal_or_none(form_data['fiyat']) or 0,
            egitmen_id=_int_or_none(form_data['egitmen_id']),
            notlar=form_data['notlar'] or None,
            aktif=True,
        )
        db.session.add(k)
        db.session.commit()
        flash(f'"{k.tam_ad}" eklendi.', 'success')
        return redirect(url_for('surucu_kursu.kursiyer_detay',
                                kursiyer_id=k.id))

    return render_template(
        'surucu_kursu/kursiyer_form.html',
        hata=None, form=form_data,
        ehliyet_siniflari=EHLIYET_SINIFLARI,
        egitmenler=egitmenler, baslik='Yeni Kursiyer',
    )


# === Kursiyer detay ===

@surucu_kursu_bp.route('/kursiyer/<int:kursiyer_id>')
@login_required
def kursiyer_detay(kursiyer_id):
    _surucu_kursu_tenant_required()
    k = Kursiyer.query.get_or_404(kursiyer_id)
    return render_template(
        'surucu_kursu/kursiyer_detay.html',
        kursiyer=k,
        ehliyet_dict=EHLIYET_SINIF_DICT,
    )


# === Kursiyer duzenle ===

@surucu_kursu_bp.route('/kursiyer/<int:kursiyer_id>/duzenle',
                        methods=['GET', 'POST'])
@login_required
def kursiyer_duzenle(kursiyer_id):
    _surucu_kursu_tenant_required()
    k = Kursiyer.query.get_or_404(kursiyer_id)

    egitmenler = User.query.filter(
        User.aktif.is_(True),
        User.rol.in_(['admin', 'yonetici', 'ogretmen']),
    ).order_by(User.ad, User.soyad).all()

    form_data = {
        'ad': k.ad, 'soyad': k.soyad, 'telefon': k.telefon or '',
        'kayit_tarihi': k.kayit_tarihi.isoformat() if k.kayit_tarihi else '',
        'ehliyet_sinifi': k.ehliyet_sinifi,
        'ders_sayisi': str(k.ders_sayisi) if k.ders_sayisi is not None else '',
        'fiyat': str(k.fiyat) if k.fiyat is not None else '',
        'egitmen_id': str(k.egitmen_id) if k.egitmen_id else '',
        'notlar': k.notlar or '',
    }
    hata = None

    if request.method == 'POST':
        for key in form_data:
            form_data[key] = (request.form.get(key) or '').strip()

        ad = form_data['ad']
        soyad = form_data['soyad']
        ehliyet_sinifi = form_data['ehliyet_sinifi']
        kayit_tarihi = _date_or_none(form_data['kayit_tarihi']) or k.kayit_tarihi

        if not ad or not soyad:
            hata = 'Ad ve soyad zorunludur.'
        elif ehliyet_sinifi not in EHLIYET_SINIF_DICT:
            hata = 'Geçerli bir ehliyet sınıfı seçin.'

        if not hata:
            k.ad = ad
            k.soyad = soyad
            k.telefon = form_data['telefon'] or None
            k.kayit_tarihi = kayit_tarihi
            k.ehliyet_sinifi = ehliyet_sinifi
            k.ders_sayisi = _int_or_none(form_data['ders_sayisi'])
            k.fiyat = _decimal_or_none(form_data['fiyat']) or 0
            k.egitmen_id = _int_or_none(form_data['egitmen_id'])
            k.notlar = form_data['notlar'] or None
            db.session.commit()
            flash('Kursiyer güncellendi.', 'success')
            return redirect(url_for('surucu_kursu.kursiyer_detay',
                                     kursiyer_id=k.id))

    return render_template(
        'surucu_kursu/kursiyer_form.html',
        hata=hata, form=form_data,
        ehliyet_siniflari=EHLIYET_SINIFLARI,
        egitmenler=egitmenler,
        baslik=f'Kursiyer Düzenle — {k.tam_ad}',
        kursiyer=k,
    )


# === Kursiyer durum (aktif/pasif) ===

@surucu_kursu_bp.route('/kursiyer/<int:kursiyer_id>/durum', methods=['POST'])
@login_required
def kursiyer_durum(kursiyer_id):
    _surucu_kursu_tenant_required()
    k = Kursiyer.query.get_or_404(kursiyer_id)
    k.aktif = not k.aktif
    db.session.commit()
    flash(f'"{k.tam_ad}" {"aktifleştirildi" if k.aktif else "pasifleştirildi"}.',
          'success')
    return redirect(url_for('surucu_kursu.kursiyer_detay', kursiyer_id=k.id))
