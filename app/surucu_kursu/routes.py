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
    KursiyerTaksit, SurucuSinavOturumu, SurucuSinavHarciKaydi,
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


# === Taksit yonetimi (egitim ucreti) ===

@surucu_kursu_bp.route('/kursiyer/<int:kursiyer_id>/taksit/plan',
                        methods=['POST'])
@login_required
def taksit_plan_olustur(kursiyer_id):
    """Birden fazla taksiti tek formdan kaydet.

    Form alanlari (her sira icin):
        vade_tarihi[1], tutar[1], vade_tarihi[2], tutar[2], ...
    Mevcut taksitler silinmez — uzerine eklenir. Eger kullanici sifirdan
    plan kurmak istiyorsa once tek tek silmeli.
    """
    _surucu_kursu_tenant_required()
    k = Kursiyer.query.get_or_404(kursiyer_id)

    # Mevcut son sira numarasi
    son_sira = db.session.query(func.coalesce(func.max(KursiyerTaksit.sira), 0)) \
        .filter(KursiyerTaksit.kursiyer_id == k.id).scalar() or 0

    eklenen = 0
    # Form'dan gelen vade_tarihi[N] ve tutar[N] ciftlerini sirayla oku
    indeksler = sorted({
        int(key.split('[')[1].rstrip(']'))
        for key in request.form.keys()
        if key.startswith('vade_tarihi[') and key.endswith(']')
    })
    for idx in indeksler:
        vade = _date_or_none(request.form.get(f'vade_tarihi[{idx}]'))
        tutar = _decimal_or_none(request.form.get(f'tutar[{idx}]'))
        if vade is None or tutar is None or tutar <= 0:
            continue
        son_sira += 1
        db.session.add(KursiyerTaksit(
            kursiyer_id=k.id,
            sira=son_sira,
            vade_tarihi=vade,
            tutar=tutar,
        ))
        eklenen += 1
    if eklenen:
        db.session.commit()
        flash(f'{eklenen} taksit eklendi.', 'success')
    else:
        flash('Geçerli taksit bulunamadı (tarih ve tutar zorunlu).', 'warning')
    return redirect(url_for('surucu_kursu.kursiyer_detay', kursiyer_id=k.id))


@surucu_kursu_bp.route(
    '/kursiyer/<int:kursiyer_id>/taksit/<int:taksit_id>/odendi',
    methods=['POST'])
@login_required
def taksit_odendi(kursiyer_id, taksit_id):
    """Taksiti odendi (toggle) olarak isaretle."""
    _surucu_kursu_tenant_required()
    t = KursiyerTaksit.query.filter_by(
        id=taksit_id, kursiyer_id=kursiyer_id
    ).first_or_404()
    t.odendi_mi = not t.odendi_mi
    if t.odendi_mi:
        t.odeme_tarihi = date.today()
    else:
        t.odeme_tarihi = None
    db.session.commit()
    flash(
        f'{t.sira}. taksit {"ödendi olarak işaretlendi" if t.odendi_mi else "ödenmedi yapıldı"}.',
        'success',
    )
    return redirect(url_for('surucu_kursu.kursiyer_detay',
                             kursiyer_id=kursiyer_id))


@surucu_kursu_bp.route(
    '/kursiyer/<int:kursiyer_id>/taksit/<int:taksit_id>/sil',
    methods=['POST'])
@login_required
def taksit_sil(kursiyer_id, taksit_id):
    _surucu_kursu_tenant_required()
    t = KursiyerTaksit.query.filter_by(
        id=taksit_id, kursiyer_id=kursiyer_id
    ).first_or_404()
    sira = t.sira
    db.session.delete(t)
    db.session.commit()
    flash(f'{sira}. taksit silindi.', 'success')
    return redirect(url_for('surucu_kursu.kursiyer_detay',
                             kursiyer_id=kursiyer_id))


# === Sinav harci yonetimi ===

@surucu_kursu_bp.route('/sinav-harc/')
@login_required
def sinav_harc_liste():
    _surucu_kursu_tenant_required()
    oturumlar = SurucuSinavOturumu.query.order_by(
        SurucuSinavOturumu.sinav_tarihi.desc()
    ).all()
    # Her oturum icin borclu/tahsil sayilari
    ozet = {}
    for o in oturumlar:
        borclu = SurucuSinavHarciKaydi.query.filter_by(
            sinav_oturum_id=o.id, durum='aday_borclu'
        ).count()
        tahsil = SurucuSinavHarciKaydi.query.filter_by(
            sinav_oturum_id=o.id, durum='tahsil_edildi'
        ).count()
        ozet[o.id] = {'borclu': borclu, 'tahsil': tahsil}
    return render_template(
        'surucu_kursu/sinav_harc_liste.html',
        oturumlar=oturumlar, ozet=ozet,
    )


@surucu_kursu_bp.route('/sinav-harc/yeni', methods=['GET', 'POST'])
@login_required
def sinav_harc_yeni():
    _surucu_kursu_tenant_required()
    form_data = {'sinav_tarihi': date.today().isoformat(),
                 'sinav_tipi': 'yazili', 'notlar': ''}
    hata = None
    if request.method == 'POST':
        form_data['sinav_tarihi'] = (request.form.get('sinav_tarihi') or '').strip()
        form_data['sinav_tipi'] = (request.form.get('sinav_tipi') or '').strip()
        form_data['notlar'] = (request.form.get('notlar') or '').strip()

        sinav_tarihi = _date_or_none(form_data['sinav_tarihi'])
        if not sinav_tarihi:
            hata = 'Sınav tarihi zorunlu.'
        elif form_data['sinav_tipi'] not in ('yazili', 'direksiyon'):
            hata = 'Geçerli sınav tipi seçin.'

        if not hata:
            o = SurucuSinavOturumu(
                sinav_tarihi=sinav_tarihi,
                sinav_tipi=form_data['sinav_tipi'],
                notlar=form_data['notlar'] or None,
            )
            db.session.add(o)
            db.session.commit()
            flash(f'Sınav oturumu oluşturuldu '
                  f'({sinav_tarihi.strftime("%d.%m.%Y")} '
                  f'{o.sinav_tipi_str}). Şimdi kalan adayları ekleyebilirsiniz.',
                  'success')
            return redirect(url_for('surucu_kursu.sinav_harc_detay',
                                     oturum_id=o.id))

    return render_template(
        'surucu_kursu/sinav_harc_yeni.html',
        hata=hata, form=form_data,
        sinav_tipleri=SurucuSinavOturumu.SINAV_TIPLERI,
    )


@surucu_kursu_bp.route('/sinav-harc/<int:oturum_id>')
@login_required
def sinav_harc_detay(oturum_id):
    _surucu_kursu_tenant_required()
    o = SurucuSinavOturumu.query.get_or_404(oturum_id)

    harc_kayitlari = SurucuSinavHarciKaydi.query.filter_by(
        sinav_oturum_id=o.id
    ).order_by(SurucuSinavHarciKaydi.id.desc()).all()
    eklenen_kursiyer_ids = {h.kursiyer_id for h in harc_kayitlari}

    # Henuz eklenmemis aktif kursiyerleri ekleme combobox'i icin
    eklenebilir = Kursiyer.query.filter(
        Kursiyer.aktif.is_(True),
        ~Kursiyer.id.in_(eklenen_kursiyer_ids) if eklenen_kursiyer_ids else True,
    ).order_by(Kursiyer.ad, Kursiyer.soyad).all()

    toplam_borc = sum(
        (h.ucret or 0) for h in harc_kayitlari if h.durum == 'aday_borclu'
    )
    toplam_tahsil = sum(
        (h.ucret or 0) for h in harc_kayitlari if h.durum == 'tahsil_edildi'
    )
    return render_template(
        'surucu_kursu/sinav_harc_detay.html',
        oturum=o, harc_kayitlari=harc_kayitlari,
        eklenebilir=eklenebilir,
        toplam_borc=toplam_borc, toplam_tahsil=toplam_tahsil,
    )


@surucu_kursu_bp.route('/sinav-harc/<int:oturum_id>/aday-ekle',
                        methods=['POST'])
@login_required
def sinav_harc_aday_ekle(oturum_id):
    _surucu_kursu_tenant_required()
    o = SurucuSinavOturumu.query.get_or_404(oturum_id)

    kursiyer_ids = request.form.getlist('kursiyer_id')
    ucret = _decimal_or_none(request.form.get('ucret')) or Decimal('0')

    eklenen = 0
    for kid in kursiyer_ids:
        kid_int = _int_or_none(kid)
        if not kid_int:
            continue
        # Cifte ekleme onle
        mevcut = SurucuSinavHarciKaydi.query.filter_by(
            sinav_oturum_id=o.id, kursiyer_id=kid_int
        ).first()
        if mevcut:
            continue
        # Kursiyer bu tenant'ta mevcut mu?
        if not Kursiyer.query.filter_by(id=kid_int).first():
            continue
        db.session.add(SurucuSinavHarciKaydi(
            sinav_oturum_id=o.id,
            kursiyer_id=kid_int,
            ucret=ucret,
            durum='aday_borclu',
        ))
        eklenen += 1
    if eklenen:
        db.session.commit()
        flash(f'{eklenen} aday eklendi (borçlu olarak).', 'success')
    else:
        flash('Aday eklenmedi (zaten mevcut veya seçilmemiş).', 'warning')
    return redirect(url_for('surucu_kursu.sinav_harc_detay',
                             oturum_id=o.id))


@surucu_kursu_bp.route(
    '/sinav-harc/<int:oturum_id>/harc/<int:harc_id>/tahsil',
    methods=['POST'])
@login_required
def sinav_harc_tahsil(oturum_id, harc_id):
    _surucu_kursu_tenant_required()
    h = SurucuSinavHarciKaydi.query.filter_by(
        id=harc_id, sinav_oturum_id=oturum_id
    ).first_or_404()
    if h.durum == 'tahsil_edildi':
        h.durum = 'aday_borclu'
        h.tahsil_tarihi = None
        flash('Tahsilat geri alındı.', 'info')
    else:
        h.durum = 'tahsil_edildi'
        h.tahsil_tarihi = date.today()
        flash(f'{h.kursiyer.tam_ad} sınav harcı tahsil edildi.', 'success')
    db.session.commit()
    return redirect(url_for('surucu_kursu.sinav_harc_detay',
                             oturum_id=oturum_id))


@surucu_kursu_bp.route(
    '/sinav-harc/<int:oturum_id>/harc/<int:harc_id>/sil',
    methods=['POST'])
@login_required
def sinav_harc_kayit_sil(oturum_id, harc_id):
    _surucu_kursu_tenant_required()
    h = SurucuSinavHarciKaydi.query.filter_by(
        id=harc_id, sinav_oturum_id=oturum_id
    ).first_or_404()
    db.session.delete(h)
    db.session.commit()
    flash('Kayıt silindi.', 'info')
    return redirect(url_for('surucu_kursu.sinav_harc_detay',
                             oturum_id=oturum_id))


@surucu_kursu_bp.route('/sinav-harc/<int:oturum_id>/sil', methods=['POST'])
@login_required
def sinav_harc_oturum_sil(oturum_id):
    _surucu_kursu_tenant_required()
    o = SurucuSinavOturumu.query.get_or_404(oturum_id)
    tarih = o.sinav_tarihi.strftime('%d.%m.%Y')
    db.session.delete(o)  # cascade ile harc_kayitlari da silinir
    db.session.commit()
    flash(f'{tarih} sınav oturumu silindi.', 'info')
    return redirect(url_for('surucu_kursu.sinav_harc_liste'))
