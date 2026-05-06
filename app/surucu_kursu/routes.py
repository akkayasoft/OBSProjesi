"""Surucu kursu modulu route'lari.

Sadece kurum_tipi='surucu_kursu' tenant'larinda menude gorunur,
ama URL'ler her tenant'ta calisir (yetkili kullanici varsa). Mevcut
OBS'i etkilememek icin /surucu-kursu/ prefix'i kullanilir.
"""
from collections import defaultdict
from datetime import date, datetime, timedelta
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
    KursiyerEhliyet, KursiyerYonlendirme, Donem, KomisyonOdemesi,
)
from app.models.muhasebe import (
    GelirGiderKaydi, GelirGiderKategorisi, BankaHesabi,
)


# === Sinav harci -> Muhasebe otomatik baglanti ===

SINAV_HARC_KATEGORI_ADI = 'Sınav Harç Tahsilatı'


def _sinav_harc_kategorisi_getir():
    """Sinav harci icin gelir kategorisini getir; yoksa olustur."""
    kat = GelirGiderKategorisi.query.filter_by(
        ad=SINAV_HARC_KATEGORI_ADI, tur='gelir',
    ).first()
    if kat is None:
        kat = GelirGiderKategorisi(
            ad=SINAV_HARC_KATEGORI_ADI, tur='gelir', aktif=True,
        )
        db.session.add(kat)
        db.session.flush()
    return kat


def _muhasebe_kaydi_olustur(harc):
    """Sinav harci tahsil edildiginde otomatik gelir kaydi olustur ve
    harc'a baglantiyi kaydet. Eger zaten bagli bir kayit varsa hicbir
    sey yapma."""
    if harc.gelir_gider_kayit_id:
        return  # zaten bagli
    kat = _sinav_harc_kategorisi_getir()
    banka = BankaHesabi.query.order_by(BankaHesabi.id.asc()).first()
    kursiyer = harc.kursiyer
    oturum = harc.sinav_oturum
    aciklama = (
        f'{kursiyer.tam_ad} — '
        f'{oturum.sinav_tarihi.strftime("%d.%m.%Y")} '
        f'{oturum.sinav_tipi_str} 2. harç'
    )
    kayit = GelirGiderKaydi(
        tur='gelir',
        kategori_id=kat.id,
        tutar=harc.ucret or 0,
        aciklama=aciklama,
        tarih=harc.tahsil_tarihi or date.today(),
        belge_no=f'SHARC-{harc.id}',
        banka_hesap_id=banka.id if banka else None,
        olusturan_id=current_user.id,
    )
    db.session.add(kayit)
    db.session.flush()
    harc.gelir_gider_kayit_id = kayit.id


def _muhasebe_kaydi_temizle(harc):
    """Eger harc'a bagli muhasebe kaydi varsa sil ve baglantiyi kopar.
    Muhasebe ekraninda elle silinmisse de guvenli — None doner."""
    if not harc.gelir_gider_kayit_id:
        return
    kayit = GelirGiderKaydi.query.filter_by(
        id=harc.gelir_gider_kayit_id,
    ).first()
    if kayit:
        db.session.delete(kayit)
    harc.gelir_gider_kayit_id = None


# === Kursiyer egitim ucreti taksiti -> Muhasebe otomatik baglanti ===

KURSIYER_GELIRI_KATEGORI_ADI = 'Sürücü Kursu Geliri'


def _kursiyer_geliri_kategorisi_getir():
    kat = GelirGiderKategorisi.query.filter_by(
        ad=KURSIYER_GELIRI_KATEGORI_ADI, tur='gelir',
    ).first()
    if kat is None:
        kat = GelirGiderKategorisi(
            ad=KURSIYER_GELIRI_KATEGORI_ADI, tur='gelir', aktif=True,
        )
        db.session.add(kat)
        db.session.flush()
    return kat


def _kursiyer_taksit_gelir_kaydi_olustur(taksit):
    """Kursiyer taksiti odendi olarak isaretlendiginde otomatik gelir
    kaydi olustur. Idempotent — zaten linkli ise atla."""
    if taksit.gelir_gider_kayit_id:
        return None
    kat = _kursiyer_geliri_kategorisi_getir()
    kursiyer = taksit.kursiyer
    aciklama = (
        f'{kursiyer.tam_ad} — {taksit.sira}. taksit ödemesi '
        f'({kursiyer.ehliyet_sinifi_str})'
    )
    kayit = GelirGiderKaydi(
        tur='gelir',
        kategori_id=kat.id,
        tutar=taksit.tutar,
        aciklama=aciklama,
        tarih=taksit.odeme_tarihi or date.today(),
        belge_no=f'KT-{taksit.id}',
        banka_hesap_id=None,  # surucu kursu kursiyer odemesi nakit varsayim
        olusturan_id=current_user.id,
    )
    db.session.add(kayit)
    db.session.flush()
    taksit.gelir_gider_kayit_id = kayit.id
    return kayit


def _kursiyer_taksit_gelir_kaydi_temizle(taksit):
    """Taksit odendi'den geri alindiginda veya silindiginde bagli
    gelir kaydini temizle."""
    if not taksit.gelir_gider_kayit_id:
        return
    kayit = GelirGiderKaydi.query.filter_by(
        id=taksit.gelir_gider_kayit_id,
    ).first()
    if kayit:
        db.session.delete(kayit)
    taksit.gelir_gider_kayit_id = None


def _kursiyer_taksit_gelir_kaydi_sync(taksit):
    """Taksit duzenlendikten sonra (tutar/tarih degisti), bagli muhasebe
    kaydinin alanlarini guncelle. Bagli kayit yoksa hicbir sey yapma."""
    if not taksit.gelir_gider_kayit_id:
        return
    kayit = GelirGiderKaydi.query.filter_by(
        id=taksit.gelir_gider_kayit_id,
    ).first()
    if kayit is None:
        # muhasebe ekraninda silinmis — link'i kopar
        taksit.gelir_gider_kayit_id = None
        return
    kayit.tutar = taksit.tutar
    if taksit.odeme_tarihi:
        kayit.tarih = taksit.odeme_tarihi
    kursiyer = taksit.kursiyer
    if kursiyer is not None:
        kayit.aciklama = (
            f'{kursiyer.tam_ad} — {taksit.sira}. taksit ödemesi '
            f'({kursiyer.ehliyet_sinifi_str})'
        )


def _surucu_kursu_tenant_required():
    """Tenant kurum_tipi 'surucu_kursu' degilse 404. Bu blueprint sadece
    surucu kursu tenant'larinda kullanilmali."""
    tenant = getattr(g, 'tenant', None)
    if tenant is None or getattr(tenant, 'kurum_tipi', 'dershane') != 'surucu_kursu':
        abort(404)


# URL prefix'leri -> modul_key esleme (yetkilendirme icin)
# Yonetici, yetkilendirme sayfasindan rolun bu modullere erisimini
# kapatabilir; o zaman before_request kontrolu 403 doner.
_SURUCU_URL_GATES = [
    ('/surucu-kursu/kursiyer',     'surucu_kursiyer'),
    ('/surucu-kursu/donem',        'surucu_kursiyer'),
    ('/surucu-kursu/makbuz',       'surucu_kursiyer'),
    ('/surucu-kursu/sinav-harc',   'surucu_sinav_harc'),
    ('/surucu-kursu/yonlendirme',  'surucu_yonlendirme'),
    ('/surucu-kursu/komisyon',     'surucu_yonlendirme'),
    ('/surucu-kursu/rapor',        'surucu_rapor'),
]


@surucu_kursu_bp.before_request
def _surucu_kursu_modul_izni_kontrol():
    """Surucu kursu URL'leri icin rol-bazli modul izni kontrolu.

    - Admin ve yonetici hep gecer (yetkilendirme sayfasini kullanan onlar).
    - Diger rollerde (egitmen/muhasebeci/...) URL'in modul_key'i
      RolModulIzin'de aktif degilse 403.
    - Modul_key eslesmiyorsa (ana sayfa, ayarlar) gecerli — bu
      sayfalar zaten kendi guard'larini kullanir.
    """
    if not current_user.is_authenticated:
        return  # login_required kontrolune birak
    if current_user.rol in ('admin', 'yonetici'):
        return  # admin/yonetici hep erisebilir
    path = request.path or ''
    modul_key = None
    for prefix, mk in _SURUCU_URL_GATES:
        if path == prefix or path.startswith(prefix + '/'):
            modul_key = mk
            break
    if modul_key is None:
        return  # eslesme yok - ana sayfa, ayarlar vs.
    from app.models.ayarlar import RolModulIzin
    if not RolModulIzin.izin_var_mi(current_user.rol, modul_key):
        abort(403)


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


def _tc_kimlik_dogrula(tc):
    """TC kimlik numarasi dogrulama (algoritmik).

    Kurallar:
    - 11 haneli, sayisal
    - Ilk hane 0 olamaz
    - 10. hane: ((1+3+5+7+9. haneler)*7 - (2+4+6+8. haneler)) mod 10
    - 11. hane: (1..10. haneler toplami) mod 10
    - Son hane cift sayi olmali

    Donus: (gecerli_mi: bool, hata_mesaji: str | None)
    """
    if tc is None or tc == '':
        return True, None  # Bos kabul edilir (nullable)
    tc = str(tc).strip()
    if not tc.isdigit() or len(tc) != 11:
        return False, 'TC kimlik 11 haneli sayisal olmalı.'
    if tc[0] == '0':
        return False, 'TC kimlik 0 ile başlayamaz.'
    rakamlar = [int(c) for c in tc]
    if int(tc[-1]) % 2 != 0:
        return False, 'Geçersiz TC kimlik (son hane çift olmalı).'
    tek_toplam = rakamlar[0] + rakamlar[2] + rakamlar[4] + rakamlar[6] + rakamlar[8]
    cift_toplam = rakamlar[1] + rakamlar[3] + rakamlar[5] + rakamlar[7]
    if (tek_toplam * 7 - cift_toplam) % 10 != rakamlar[9]:
        return False, 'Geçersiz TC kimlik numarası (sağlama hatası).'
    if sum(rakamlar[:10]) % 10 != rakamlar[10]:
        return False, 'Geçersiz TC kimlik numarası (sağlama hatası).'
    return True, None


def _donem_getir_veya_olustur(yil: int, ay: int) -> Donem:
    """Verilen yil/ay icin Donem'i getir; yoksa olustur ve kaydet.

    Idempotent: ayni yil+ay icin tekrar cagrilirsa mevcut kaydi doner.
    Cagiranin ayrica db.session.commit() yapmasi gerekmez (zaten
    flush yapmiyor — caller'in transaction'ina katiliyor).
    """
    d = Donem.query.filter_by(yil=yil, ay=ay).first()
    if d is None:
        d = Donem.from_yil_ay(yil, ay)
        db.session.add(d)
        db.session.flush()  # d.id elde etmek icin
    return d


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
        # Hem birincil ehliyet (geriye uyum) hem de KursiyerEhliyet
        # uzerinden eslesme - kursiyer iki yerden de gozukmesin diye
        # exists subquery kullaniyoruz.
        ek_eslesme = db.session.query(KursiyerEhliyet.kursiyer_id).filter(
            KursiyerEhliyet.ehliyet_sinifi == sinif,
        ).subquery()
        q = q.filter(or_(
            Kursiyer.ehliyet_sinifi == sinif,
            Kursiyer.id.in_(ek_eslesme),
        ))

    donem_id_str = (request.args.get('donem') or '').strip()
    donem_id = None
    if donem_id_str:
        try:
            donem_id = int(donem_id_str)
            q = q.filter(Kursiyer.donem_id == donem_id)
        except ValueError:
            donem_id = None

    if arama:
        like = f'%{arama}%'
        q = q.filter(or_(
            Kursiyer.ad.ilike(like),
            Kursiyer.soyad.ilike(like),
            Kursiyer.telefon.ilike(like),
            Kursiyer.tc_kimlik.ilike(like),
        ))

    kursiyerler = q.order_by(Kursiyer.id.desc()).all()
    toplam = Kursiyer.query.filter(Kursiyer.aktif.is_(True)).count()

    # Donem dropdown icin tum donemleri getir (yeniden eskiye)
    donemler = Donem.query.order_by(
        Donem.yil.desc(), Donem.ay.desc()
    ).all()

    return render_template(
        'surucu_kursu/kursiyer_liste.html',
        kursiyerler=kursiyerler,
        ehliyet_siniflari=EHLIYET_SINIFLARI,
        ehliyet_dict=EHLIYET_SINIF_DICT,
        donemler=donemler,
        arama=arama, sinif=sinif, durum=durum, donem=donem_id,
        toplam_aktif=toplam,
    )


# === Kursiyer yeni ===

@surucu_kursu_bp.route('/kursiyer/yeni', methods=['GET', 'POST'])
@login_required
def kursiyer_yeni():
    """Yeni kursiyer kaydi - SADECE kisisel bilgiler.

    Ehliyet/ders/fiyat/egitmen bilgileri kayit sonrasi detay sayfasinda
    'Ehliyetler' kartindan eklenir.
    """
    _surucu_kursu_tenant_required()

    form_data = {
        'ad': '', 'soyad': '', 'tc_kimlik': '', 'telefon': '',
        'kayit_tarihi': date.today().isoformat(),
        'notlar': '',
    }
    hata = None

    if request.method == 'POST':
        for k in form_data:
            form_data[k] = (request.form.get(k) or '').strip()

        ad = form_data['ad']
        soyad = form_data['soyad']
        tc_kimlik = form_data['tc_kimlik']
        kayit_tarihi = _date_or_none(form_data['kayit_tarihi']) or date.today()

        if not ad or not soyad:
            hata = 'Ad ve soyad zorunludur.'
        else:
            tc_ok, tc_hata = _tc_kimlik_dogrula(tc_kimlik)
            if not tc_ok:
                hata = tc_hata

        if hata:
            return render_template(
                'surucu_kursu/kursiyer_form.html',
                hata=hata, form=form_data,
                baslik='Yeni Kursiyer',
            )

        # Donem - kayit_tarihi'ne gore otomatik atama
        donem = _donem_getir_veya_olustur(kayit_tarihi.year,
                                            kayit_tarihi.month)

        k = Kursiyer(
            ad=ad, soyad=soyad,
            tc_kimlik=tc_kimlik or None,
            telefon=form_data['telefon'] or None,
            kayit_tarihi=kayit_tarihi,
            ehliyet_sinifi=None,   # ehliyetler sonra eklenecek
            ders_sayisi=None,
            fiyat=0,
            egitmen_id=None,
            notlar=form_data['notlar'] or None,
            donem_id=donem.id,
            aktif=True,
        )
        db.session.add(k)
        db.session.commit()
        flash(f'"{k.tam_ad}" kaydedildi. Şimdi profilden ehliyetlerini '
              f'ekleyebilirsiniz.', 'success')
        return redirect(url_for('surucu_kursu.kursiyer_detay',
                                kursiyer_id=k.id))

    return render_template(
        'surucu_kursu/kursiyer_form.html',
        hata=None, form=form_data,
        baslik='Yeni Kursiyer',
    )


# === Kursiyer detay ===

@surucu_kursu_bp.route('/kursiyer/<int:kursiyer_id>')
@login_required
def kursiyer_detay(kursiyer_id):
    _surucu_kursu_tenant_required()
    k = Kursiyer.query.get_or_404(kursiyer_id)
    egitmenler = User.query.filter(
        User.aktif.is_(True),
        User.rol.in_(['admin', 'yonetici', 'ogretmen']),
    ).order_by(User.ad, User.soyad).all()
    # Mevcut ehliyet kodlari (cakisma onleme icin)
    mevcut_ehliyet_kodlari = {k.ehliyet_sinifi}
    for e in k.ek_ehliyetler:
        mevcut_ehliyet_kodlari.add(e.ehliyet_sinifi)
    # Yonlendirmeler — en yeniden eskiye
    yonlendirmeler = k.yonlendirmeler.all()
    return render_template(
        'surucu_kursu/kursiyer_detay.html',
        kursiyer=k,
        ehliyet_dict=EHLIYET_SINIF_DICT,
        ehliyet_siniflari=EHLIYET_SINIFLARI,
        egitmenler=egitmenler,
        mevcut_ehliyet_kodlari=mevcut_ehliyet_kodlari,
        yonlendirmeler=yonlendirmeler,
        yonlendirme_durumlar=KursiyerYonlendirme.DURUMLAR,
        bugun=date.today(),
    )


# === Kursiyer duzenle ===

@surucu_kursu_bp.route('/kursiyer/<int:kursiyer_id>/duzenle',
                        methods=['GET', 'POST'])
@login_required
def kursiyer_duzenle(kursiyer_id):
    """Kursiyer kisisel bilgilerini duzenle.

    Ehliyet/ders/fiyat/egitmen detay sayfasindan yonetilir.
    """
    _surucu_kursu_tenant_required()
    k = Kursiyer.query.get_or_404(kursiyer_id)

    form_data = {
        'ad': k.ad, 'soyad': k.soyad,
        'tc_kimlik': k.tc_kimlik or '',
        'telefon': k.telefon or '',
        'kayit_tarihi': k.kayit_tarihi.isoformat() if k.kayit_tarihi else '',
        'notlar': k.notlar or '',
    }
    hata = None

    if request.method == 'POST':
        for key in form_data:
            form_data[key] = (request.form.get(key) or '').strip()

        ad = form_data['ad']
        soyad = form_data['soyad']
        tc_kimlik = form_data['tc_kimlik']
        kayit_tarihi = _date_or_none(form_data['kayit_tarihi']) or k.kayit_tarihi

        if not ad or not soyad:
            hata = 'Ad ve soyad zorunludur.'
        else:
            tc_ok, tc_hata = _tc_kimlik_dogrula(tc_kimlik)
            if not tc_ok:
                hata = tc_hata

        if not hata:
            k.ad = ad
            k.soyad = soyad
            k.tc_kimlik = tc_kimlik or None
            k.telefon = form_data['telefon'] or None
            # Donem - kayit_tarihi degistiyse yeniden ata
            eski_yil_ay = (k.kayit_tarihi.year, k.kayit_tarihi.month) \
                if k.kayit_tarihi else (None, None)
            yeni_yil_ay = (kayit_tarihi.year, kayit_tarihi.month)
            k.kayit_tarihi = kayit_tarihi
            if eski_yil_ay != yeni_yil_ay or not k.donem_id:
                d = _donem_getir_veya_olustur(kayit_tarihi.year,
                                                kayit_tarihi.month)
                k.donem_id = d.id
            k.notlar = form_data['notlar'] or None
            db.session.commit()
            flash('Kursiyer güncellendi.', 'success')
            return redirect(url_for('surucu_kursu.kursiyer_detay',
                                     kursiyer_id=k.id))

    return render_template(
        'surucu_kursu/kursiyer_form.html',
        hata=hata, form=form_data,
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


def _kursiyer_makbuz_no_uret():
    """KSR-YYYYMMDD-NNNN formatinda benzersiz makbuz numarasi."""
    bugun = datetime.now().strftime('%Y%m%d')
    prefix = f'KSR-{bugun}-'
    son = KursiyerTaksit.query.filter(
        KursiyerTaksit.makbuz_no.like(f'{prefix}%'),
    ).order_by(KursiyerTaksit.makbuz_no.desc()).first()
    if son and son.makbuz_no:
        try:
            son_no = int(son.makbuz_no.split('-')[-1])
            yeni = son_no + 1
        except (ValueError, IndexError):
            yeni = 1
    else:
        yeni = 1
    return f'{prefix}{yeni:04d}'


@surucu_kursu_bp.route(
    '/kursiyer/<int:kursiyer_id>/taksit/<int:taksit_id>/odeme-al',
    methods=['POST'])
@login_required
def taksit_odeme_al(kursiyer_id, taksit_id):
    """Bir taksit icin odeme al — modal'dan tarih, yontem, odeyen ad alir,
    makbuz numarasi uretir, otomatik gelir kaydi olusturur."""
    _surucu_kursu_tenant_required()
    t = KursiyerTaksit.query.filter_by(
        id=taksit_id, kursiyer_id=kursiyer_id
    ).first_or_404()

    if t.odendi_mi:
        flash('Bu taksit zaten ödenmiş.', 'warning')
        return redirect(url_for('surucu_kursu.kursiyer_detay',
                                 kursiyer_id=kursiyer_id))

    odeme_tarihi = _date_or_none(request.form.get('odeme_tarihi')) or date.today()
    odeme_turu = (request.form.get('odeme_turu') or '').strip()
    odeyen_ad = (request.form.get('odeyen_ad') or '').strip()
    yeni_tutar = _decimal_or_none(request.form.get('tutar'))

    valid_turler = {kod for kod, _ in t.ODEME_TURLERI}
    if odeme_turu not in valid_turler:
        flash('Geçerli bir ödeme yöntemi seçin (Nakit / EFT / Kredi Kartı).',
              'danger')
        return redirect(url_for('surucu_kursu.kursiyer_detay',
                                 kursiyer_id=kursiyer_id))

    # Tutar override (kismi odeme degil — taksit tutarini guncelle)
    if yeni_tutar is not None and yeni_tutar > 0:
        t.tutar = yeni_tutar

    t.odendi_mi = True
    t.odeme_tarihi = odeme_tarihi
    t.odeme_turu = odeme_turu
    t.odeyen_ad = odeyen_ad or t.kursiyer.tam_ad
    t.teslim_alan_id = current_user.id
    t.makbuz_no = _kursiyer_makbuz_no_uret()

    db.session.flush()
    _kursiyer_taksit_gelir_kaydi_olustur(t)
    db.session.commit()

    flash(f'{t.sira}. taksit ödemesi alındı (Makbuz: {t.makbuz_no}). '
          f'Muhasebeye otomatik gelir kaydı eklendi.', 'success')
    # Direkt makbuz sayfasina yonlendir — yazdirilabilsin
    return redirect(url_for('surucu_kursu.taksit_makbuz',
                             kursiyer_id=kursiyer_id, taksit_id=taksit_id))


@surucu_kursu_bp.route(
    '/kursiyer/<int:kursiyer_id>/taksit/<int:taksit_id>/odeme-iptal',
    methods=['POST'])
@login_required
def taksit_odeme_iptal(kursiyer_id, taksit_id):
    """Odenmis taksiti tekrar 'odenmedi' yap. Odeme detaylari + makbuz
    no temizlenir, bagli muhasebe kaydi silinir."""
    _surucu_kursu_tenant_required()
    t = KursiyerTaksit.query.filter_by(
        id=taksit_id, kursiyer_id=kursiyer_id
    ).first_or_404()
    if not t.odendi_mi:
        flash('Bu taksit zaten ödenmemiş.', 'warning')
        return redirect(url_for('surucu_kursu.kursiyer_detay',
                                 kursiyer_id=kursiyer_id))

    # Muhasebe kaydini temizle
    _kursiyer_taksit_gelir_kaydi_temizle(t)
    eski_makbuz = t.makbuz_no

    t.odendi_mi = False
    t.odeme_tarihi = None
    t.odeme_turu = None
    t.odeyen_ad = None
    t.teslim_alan_id = None
    t.makbuz_no = None
    db.session.commit()

    flash(f'{t.sira}. taksit ödemesi iptal edildi '
          f'(makbuz {eski_makbuz} geçersiz). Muhasebe kaydı da silindi.',
          'info')
    return redirect(url_for('surucu_kursu.kursiyer_detay',
                             kursiyer_id=kursiyer_id))


@surucu_kursu_bp.route(
    '/kursiyer/<int:kursiyer_id>/taksit/<int:taksit_id>/makbuz')
@login_required
def taksit_makbuz(kursiyer_id, taksit_id):
    """Print-friendly makbuz sayfasi (A4)."""
    _surucu_kursu_tenant_required()
    t = KursiyerTaksit.query.filter_by(
        id=taksit_id, kursiyer_id=kursiyer_id
    ).first_or_404()
    if not t.odendi_mi or not t.makbuz_no:
        flash('Bu taksit henüz ödenmemiş; makbuz oluşturulamaz.', 'warning')
        return redirect(url_for('surucu_kursu.kursiyer_detay',
                                 kursiyer_id=kursiyer_id))
    tenant_obj = getattr(g, 'tenant', None)
    return render_template(
        'surucu_kursu/taksit_makbuz.html',
        taksit=t, kursiyer=t.kursiyer, tenant=tenant_obj,
    )


@surucu_kursu_bp.route(
    '/kursiyer/<int:kursiyer_id>/taksit/<int:taksit_id>/duzenle',
    methods=['POST'])
@login_required
def taksit_duzenle(kursiyer_id, taksit_id):
    """Bir taksitin vade tarihi ve/veya tutarini guncelle.
    Eger taksit odenmis ise bagli muhasebe gelir kaydi da senkronize
    edilir (tutar/tarih/aciklama)."""
    _surucu_kursu_tenant_required()
    t = KursiyerTaksit.query.filter_by(
        id=taksit_id, kursiyer_id=kursiyer_id
    ).first_or_404()

    yeni_vade = _date_or_none(request.form.get('vade_tarihi'))
    yeni_tutar = _decimal_or_none(request.form.get('tutar'))
    yeni_not = (request.form.get('odeme_notu') or '').strip()

    if yeni_vade is None:
        flash('Geçerli bir vade tarihi giriniz.', 'danger')
        return redirect(url_for('surucu_kursu.kursiyer_detay',
                                 kursiyer_id=kursiyer_id))
    if yeni_tutar is None or yeni_tutar <= 0:
        flash('Tutar 0\'dan büyük olmalı.', 'danger')
        return redirect(url_for('surucu_kursu.kursiyer_detay',
                                 kursiyer_id=kursiyer_id))

    eski_tutar = t.tutar
    eski_vade = t.vade_tarihi

    t.vade_tarihi = yeni_vade
    t.tutar = yeni_tutar
    t.odeme_notu = yeni_not or None

    # Eger odenmisse muhasebe kaydini da senkronize et
    if t.odendi_mi:
        _kursiyer_taksit_gelir_kaydi_sync(t)

    db.session.commit()
    farklar = []
    if eski_tutar != yeni_tutar:
        farklar.append(f'tutar {eski_tutar:.2f}₺ → {yeni_tutar:.2f}₺')
    if eski_vade != yeni_vade:
        farklar.append(f'vade {eski_vade} → {yeni_vade}')
    ozet = ', '.join(farklar) if farklar else 'değişiklik yok'
    flash(f'{t.sira}. taksit güncellendi ({ozet}).', 'success')
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
    # Bagli muhasebe kaydini once temizle
    _kursiyer_taksit_gelir_kaydi_temizle(t)
    db.session.delete(t)
    db.session.commit()
    flash(f'{sira}. taksit silindi (varsa bağlı muhasebe kaydı da temizlendi).',
          'success')
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
        bugun=date.today(),
        odeme_turleri=SurucuSinavHarciKaydi.ODEME_TURLERI,
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


def _sinav_harc_makbuz_no_uret():
    """SHR-YYYYMMDD-NNNN formatinda benzersiz makbuz numarasi."""
    bugun = datetime.now().strftime('%Y%m%d')
    prefix = f'SHR-{bugun}-'
    son = SurucuSinavHarciKaydi.query.filter(
        SurucuSinavHarciKaydi.makbuz_no.like(f'{prefix}%'),
    ).order_by(SurucuSinavHarciKaydi.makbuz_no.desc()).first()
    if son and son.makbuz_no:
        try:
            son_no = int(son.makbuz_no.split('-')[-1])
            yeni = son_no + 1
        except (ValueError, IndexError):
            yeni = 1
    else:
        yeni = 1
    return f'{prefix}{yeni:04d}'


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
        # Geri al — durumu degistir + bagli muhasebe kaydini sil + makbuz alanlari
        h.durum = 'aday_borclu'
        h.tahsil_tarihi = None
        h.odeme_turu = None
        h.odeyen_ad = None
        h.teslim_alan_id = None
        h.makbuz_no = None
        _muhasebe_kaydi_temizle(h)
        db.session.commit()
        flash('Tahsilat geri alındı, muhasebe kaydı ve makbuz silindi.', 'info')
        return redirect(url_for('surucu_kursu.sinav_harc_detay',
                                 oturum_id=oturum_id))

    # Tahsil et - form alanlari (modal'dan)
    odeme_turu = (request.form.get('odeme_turu') or 'nakit').strip()
    odeyen_ad = (request.form.get('odeyen_ad') or '').strip()
    tahsil_tarihi = _date_or_none(request.form.get('tahsil_tarihi')) \
        or date.today()

    if odeme_turu not in dict(SurucuSinavHarciKaydi.ODEME_TURLERI):
        flash('Geçerli bir ödeme türü seçin.', 'danger')
        return redirect(url_for('surucu_kursu.sinav_harc_detay',
                                 oturum_id=oturum_id))

    h.durum = 'tahsil_edildi'
    h.tahsil_tarihi = tahsil_tarihi
    h.odeme_turu = odeme_turu
    h.odeyen_ad = odeyen_ad or h.kursiyer.tam_ad
    h.teslim_alan_id = current_user.id
    h.makbuz_no = _sinav_harc_makbuz_no_uret()
    db.session.flush()
    _muhasebe_kaydi_olustur(h)
    db.session.commit()
    flash(f'{h.kursiyer.tam_ad} sınav harcı tahsil edildi (Makbuz: '
          f'{h.makbuz_no}). Muhasebeye otomatik gelir kaydı eklendi.',
          'success')
    return redirect(url_for('surucu_kursu.sinav_harc_makbuz',
                             oturum_id=oturum_id, harc_id=harc_id))


@surucu_kursu_bp.route(
    '/sinav-harc/<int:oturum_id>/harc/<int:harc_id>/makbuz')
@login_required
def sinav_harc_makbuz(oturum_id, harc_id):
    """Sinav harci makbuzunu A4 yazdirma sayfasiyla goster."""
    _surucu_kursu_tenant_required()
    h = SurucuSinavHarciKaydi.query.filter_by(
        id=harc_id, sinav_oturum_id=oturum_id
    ).first_or_404()
    if h.durum != 'tahsil_edildi' or not h.makbuz_no:
        flash('Bu kayda ait makbuz bulunamadı (henüz tahsil edilmemiş).',
              'warning')
        return redirect(url_for('surucu_kursu.sinav_harc_detay',
                                 oturum_id=oturum_id))
    # Tenant adi (basligin uzerinde)
    tenant = getattr(g, 'tenant', None)
    kurum_adi = getattr(tenant, 'kurum_adi', None) or getattr(
        tenant, 'ad', None) or 'Sürücü Kursu'
    return render_template(
        'surucu_kursu/sinav_harc_makbuz.html',
        harc=h, kurum_adi=kurum_adi,
    )


@surucu_kursu_bp.route(
    '/sinav-harc/<int:oturum_id>/harc/<int:harc_id>/sil',
    methods=['POST'])
@login_required
def sinav_harc_kayit_sil(oturum_id, harc_id):
    _surucu_kursu_tenant_required()
    h = SurucuSinavHarciKaydi.query.filter_by(
        id=harc_id, sinav_oturum_id=oturum_id
    ).first_or_404()
    # Bagli muhasebe kaydini once temizle
    _muhasebe_kaydi_temizle(h)
    db.session.delete(h)
    db.session.commit()
    flash('Kayıt silindi (varsa bağlı muhasebe kaydı da temizlendi).', 'info')
    return redirect(url_for('surucu_kursu.sinav_harc_detay',
                             oturum_id=oturum_id))


@surucu_kursu_bp.route('/sinav-harc/<int:oturum_id>/sil', methods=['POST'])
@login_required
def sinav_harc_oturum_sil(oturum_id):
    _surucu_kursu_tenant_required()
    o = SurucuSinavOturumu.query.get_or_404(oturum_id)
    tarih = o.sinav_tarihi.strftime('%d.%m.%Y')
    # Tum harc kayitlarinin bagli muhasebe satirlarini once temizle
    silinen_muhasebe = 0
    for h in list(o.harc_kayitlari):
        if h.gelir_gider_kayit_id:
            _muhasebe_kaydi_temizle(h)
            silinen_muhasebe += 1
    db.session.delete(o)  # cascade ile harc_kayitlari da silinir
    db.session.commit()
    if silinen_muhasebe:
        flash(f'{tarih} sınav oturumu silindi ({silinen_muhasebe} '
              f'muhasebe kaydı da temizlendi).', 'info')
    else:
        flash(f'{tarih} sınav oturumu silindi.', 'info')
    return redirect(url_for('surucu_kursu.sinav_harc_liste'))


# === Raporlama ===

@surucu_kursu_bp.route('/rapor/')
@login_required
def rapor_dashboard():
    """Surucu kursu icin kapsamli raporlama sayfasi.

    KPI kartlari + ehliyet sinifi dagilimi + egitmen performansi +
    geciken/yaklasan taksitler + sinav oturum ozeti + son 6 ay mali
    trendi tek sayfada.
    """
    _surucu_kursu_tenant_required()

    bugun = date.today()
    ay_basi = bugun.replace(day=1)
    # Son 6 ayin baslangici
    ay_geriye = ay_basi.replace(day=1)
    for _ in range(5):
        # bir onceki ayin 1'ine kay
        prev = ay_geriye - timedelta(days=1)
        ay_geriye = prev.replace(day=1)

    # === KPI'lar ===
    toplam_aktif = Kursiyer.query.filter_by(aktif=True).count()
    toplam_pasif = Kursiyer.query.filter_by(aktif=False).count()
    bu_ay_yeni = Kursiyer.query.filter(
        Kursiyer.kayit_tarihi >= ay_basi,
    ).count()

    bu_ay_gelir = float(db.session.query(
        func.coalesce(func.sum(GelirGiderKaydi.tutar), 0)
    ).filter(
        GelirGiderKaydi.tur == 'gelir',
        GelirGiderKaydi.tarih >= ay_basi,
    ).scalar() or 0)

    bu_ay_gider = float(db.session.query(
        func.coalesce(func.sum(GelirGiderKaydi.tutar), 0)
    ).filter(
        GelirGiderKaydi.tur == 'gider',
        GelirGiderKaydi.tarih >= ay_basi,
    ).scalar() or 0)

    bu_ay_net = bu_ay_gelir - bu_ay_gider

    # Bekleyen tahsilat (egitim ucreti)
    bekleyen_top = float(db.session.query(
        func.coalesce(func.sum(KursiyerTaksit.tutar), 0)
    ).filter(KursiyerTaksit.odendi_mi.is_(False)).scalar() or 0)

    # Gecikmis taksit (vadesi gecmis ve odenmemis)
    geciken_taksitler = KursiyerTaksit.query.filter(
        KursiyerTaksit.odendi_mi.is_(False),
        KursiyerTaksit.vade_tarihi < bugun,
    ).order_by(KursiyerTaksit.vade_tarihi.asc()).all()
    geciken_top = sum(float(t.tutar) for t in geciken_taksitler)
    geciken_sayi = len(geciken_taksitler)

    # Yaklasan vadeler (onumuzdeki 30 gun)
    yaklasan_taksitler = KursiyerTaksit.query.filter(
        KursiyerTaksit.odendi_mi.is_(False),
        KursiyerTaksit.vade_tarihi >= bugun,
        KursiyerTaksit.vade_tarihi <= bugun + timedelta(days=30),
    ).order_by(KursiyerTaksit.vade_tarihi.asc()).all()

    # === Ehliyet sinifi dagilimi ===
    ehliyet_dagilim_raw = db.session.query(
        Kursiyer.ehliyet_sinifi,
        func.count(Kursiyer.id),
        func.coalesce(func.sum(Kursiyer.fiyat), 0),
    ).filter(Kursiyer.aktif.is_(True)).group_by(Kursiyer.ehliyet_sinifi).all()
    ehliyet_dagilim = [
        {
            'kod': kod,
            'ad': EHLIYET_SINIF_DICT.get(kod, kod),
            'sayi': sayi,
            'toplam_fiyat': float(toplam),
        }
        for kod, sayi, toplam in ehliyet_dagilim_raw
    ]
    ehliyet_dagilim.sort(key=lambda x: -x['sayi'])

    # === Egitmen performansi ===
    egitmen_dagilim_raw = db.session.query(
        User.id, User.ad, User.soyad,
        func.count(Kursiyer.id),
        func.coalesce(func.sum(Kursiyer.fiyat), 0),
    ).outerjoin(Kursiyer, (Kursiyer.egitmen_id == User.id) &
                          (Kursiyer.aktif.is_(True))).filter(
        User.aktif.is_(True),
        User.rol.in_(['admin', 'yonetici', 'ogretmen']),
    ).group_by(User.id, User.ad, User.soyad).all()
    egitmen_dagilim = [
        {
            'ad': f'{ad} {soyad}',
            'kursiyer_sayi': sayi,
            'toplam_ciro': float(ciro),
        }
        for _, ad, soyad, sayi, ciro in egitmen_dagilim_raw
    ]
    egitmen_dagilim.sort(key=lambda x: -x['kursiyer_sayi'])

    # === Aylik kayit trendi (son 12 ay) ===
    son_12_ay = bugun - timedelta(days=365)
    kayit_listesi = db.session.query(Kursiyer.kayit_tarihi).filter(
        Kursiyer.kayit_tarihi >= son_12_ay,
    ).all()
    aylik_kayit = defaultdict(int)
    for (tarih,) in kayit_listesi:
        if tarih:
            anahtar = tarih.strftime('%Y-%m')
            aylik_kayit[anahtar] += 1
    aylik_kayit_sirali = sorted(aylik_kayit.items())

    # === Mali trend (son 6 ay) ===
    mali_kayitlar = db.session.query(
        GelirGiderKaydi.tur,
        GelirGiderKaydi.tarih,
        GelirGiderKaydi.tutar,
    ).filter(GelirGiderKaydi.tarih >= ay_geriye).all()
    mali_trend = defaultdict(lambda: {'gelir': 0.0, 'gider': 0.0})
    for tur, tarih, tutar in mali_kayitlar:
        anahtar = tarih.strftime('%Y-%m')
        mali_trend[anahtar][tur] += float(tutar or 0)
    mali_trend_sirali = []
    for anahtar in sorted(mali_trend.keys()):
        v = mali_trend[anahtar]
        mali_trend_sirali.append({
            'ay': anahtar,
            'gelir': v['gelir'], 'gider': v['gider'],
            'net': v['gelir'] - v['gider'],
        })

    # === Sinav performans ozeti (son 5 oturum) ===
    son_oturumlar = SurucuSinavOturumu.query.order_by(
        SurucuSinavOturumu.sinav_tarihi.desc()
    ).limit(5).all()
    sinav_ozet = []
    for o in son_oturumlar:
        kayitlar = list(o.harc_kayitlari)
        borclu = sum(1 for h in kayitlar if h.durum == 'aday_borclu')
        tahsil = sum(1 for h in kayitlar if h.durum == 'tahsil_edildi')
        tahsil_top = sum(float(h.ucret or 0) for h in kayitlar
                         if h.durum == 'tahsil_edildi')
        borclu_top = sum(float(h.ucret or 0) for h in kayitlar
                         if h.durum == 'aday_borclu')
        sinav_ozet.append({
            'oturum': o, 'borclu': borclu, 'tahsil': tahsil,
            'tahsil_top': tahsil_top, 'borclu_top': borclu_top,
        })

    # === Yil bazi sinav harci toplam ==
    yil_basi = date(bugun.year, 1, 1)
    yil_sinav_tahsil = float(db.session.query(
        func.coalesce(func.sum(SurucuSinavHarciKaydi.ucret), 0)
    ).filter(
        SurucuSinavHarciKaydi.durum == 'tahsil_edildi',
        SurucuSinavHarciKaydi.tahsil_tarihi >= yil_basi,
    ).scalar() or 0)
    yil_sinav_borclu = float(db.session.query(
        func.coalesce(func.sum(SurucuSinavHarciKaydi.ucret), 0)
    ).filter(SurucuSinavHarciKaydi.durum == 'aday_borclu').scalar() or 0)

    return render_template(
        'surucu_kursu/rapor.html',
        # KPI
        toplam_aktif=toplam_aktif, toplam_pasif=toplam_pasif,
        bu_ay_yeni=bu_ay_yeni,
        bu_ay_gelir=bu_ay_gelir, bu_ay_gider=bu_ay_gider,
        bu_ay_net=bu_ay_net,
        bekleyen_top=bekleyen_top,
        geciken_top=geciken_top, geciken_sayi=geciken_sayi,
        # Tablolar
        geciken_taksitler=geciken_taksitler[:20],
        yaklasan_taksitler=yaklasan_taksitler[:20],
        ehliyet_dagilim=ehliyet_dagilim,
        egitmen_dagilim=egitmen_dagilim,
        aylik_kayit=aylik_kayit_sirali,
        mali_trend=mali_trend_sirali,
        sinav_ozet=sinav_ozet,
        yil_sinav_tahsil=yil_sinav_tahsil,
        yil_sinav_borclu=yil_sinav_borclu,
        # Yardimcilar
        bugun=bugun,
    )


# === Surucu Kursu Anasayfa ===

@surucu_kursu_bp.route('/')
@login_required
def dashboard():
    """Surucu kursu icin gunluk operasyon dashboard'u.

    Rapor sayfasindan farkli olarak: 'bugun ne yapmam lazim?' odakli.
    KPI ozet + geciken taksitler (acil) + yaklasan 7 gun vadeler +
    hizli eylem butonlari.
    """
    _surucu_kursu_tenant_required()

    bugun = date.today()
    ay_basi = bugun.replace(day=1)
    yaklasan_son = bugun + timedelta(days=30)

    # KPI'lar
    aktif_kursiyer = Kursiyer.query.filter_by(aktif=True).count()
    bu_ay_yeni = Kursiyer.query.filter(
        Kursiyer.kayit_tarihi >= ay_basi,
    ).count()

    bu_ay_gelir = float(db.session.query(
        func.coalesce(func.sum(GelirGiderKaydi.tutar), 0)
    ).filter(
        GelirGiderKaydi.tur == 'gelir',
        GelirGiderKaydi.tarih >= ay_basi,
    ).scalar() or 0)
    bu_ay_gider = float(db.session.query(
        func.coalesce(func.sum(GelirGiderKaydi.tutar), 0)
    ).filter(
        GelirGiderKaydi.tur == 'gider',
        GelirGiderKaydi.tarih >= ay_basi,
    ).scalar() or 0)
    bu_ay_net = bu_ay_gelir - bu_ay_gider

    bekleyen_top = float(db.session.query(
        func.coalesce(func.sum(KursiyerTaksit.tutar), 0)
    ).filter(KursiyerTaksit.odendi_mi.is_(False)).scalar() or 0)

    # Geciken taksitler (top 10)
    geciken_taksitler = KursiyerTaksit.query.filter(
        KursiyerTaksit.odendi_mi.is_(False),
        KursiyerTaksit.vade_tarihi < bugun,
    ).order_by(KursiyerTaksit.vade_tarihi.asc()).limit(10).all()
    geciken_sayi = KursiyerTaksit.query.filter(
        KursiyerTaksit.odendi_mi.is_(False),
        KursiyerTaksit.vade_tarihi < bugun,
    ).count()
    geciken_top = float(db.session.query(
        func.coalesce(func.sum(KursiyerTaksit.tutar), 0)
    ).filter(
        KursiyerTaksit.odendi_mi.is_(False),
        KursiyerTaksit.vade_tarihi < bugun,
    ).scalar() or 0)

    # Yaklasan 30 gun
    yaklasan_taksitler = KursiyerTaksit.query.filter(
        KursiyerTaksit.odendi_mi.is_(False),
        KursiyerTaksit.vade_tarihi >= bugun,
        KursiyerTaksit.vade_tarihi <= yaklasan_son,
    ).order_by(KursiyerTaksit.vade_tarihi.asc()).all()
    yaklasan_top = sum(float(t.tutar) for t in yaklasan_taksitler)

    # Bekleyen sinav harci
    sinav_borclu_sayi = SurucuSinavHarciKaydi.query.filter_by(
        durum='aday_borclu',
    ).count()
    sinav_borclu_top = float(db.session.query(
        func.coalesce(func.sum(SurucuSinavHarciKaydi.ucret), 0)
    ).filter(
        SurucuSinavHarciKaydi.durum == 'aday_borclu',
    ).scalar() or 0)

    # Bugun yapilan tahsilatlar (bugune ozel)
    bugun_tahsilat = float(db.session.query(
        func.coalesce(func.sum(KursiyerTaksit.tutar), 0)
    ).filter(
        KursiyerTaksit.odendi_mi.is_(True),
        KursiyerTaksit.odeme_tarihi == bugun,
    ).scalar() or 0)

    return render_template(
        'surucu_kursu/dashboard.html',
        bugun=bugun,
        # KPI
        aktif_kursiyer=aktif_kursiyer,
        bu_ay_yeni=bu_ay_yeni,
        bu_ay_gelir=bu_ay_gelir,
        bu_ay_gider=bu_ay_gider,
        bu_ay_net=bu_ay_net,
        bekleyen_top=bekleyen_top,
        bugun_tahsilat=bugun_tahsilat,
        # Tablolar
        geciken_taksitler=geciken_taksitler,
        geciken_sayi=geciken_sayi,
        geciken_top=geciken_top,
        yaklasan_taksitler=yaklasan_taksitler,
        yaklasan_top=yaklasan_top,
        sinav_borclu_sayi=sinav_borclu_sayi,
        sinav_borclu_top=sinav_borclu_top,
    )


# === Toplu Kursiyer Yukleme (Faz 3.C) ===

KURSIYER_TOPLU_BASLIKLARI = [
    {'key': 'ad', 'label': 'Ad', 'zorunlu': True},
    {'key': 'soyad', 'label': 'Soyad', 'zorunlu': True},
    {'key': 'tc_kimlik', 'label': 'TC Kimlik No'},
    {'key': 'telefon', 'label': 'Telefon'},
    {'key': 'ehliyet_sinifi', 'label': 'Ehliyet Sınıfı (kod)', 'zorunlu': True},
    {'key': 'ders_sayisi', 'label': 'Ders Sayısı'},
    {'key': 'fiyat', 'label': 'Toplam Fiyat (₺)'},
    {'key': 'egitmen_username', 'label': 'Eğitmen Kullanıcı Adı'},
    {'key': 'kayit_tarihi', 'label': 'Kayıt Tarihi (YYYY-MM-DD)'},
    {'key': 'notlar', 'label': 'Notlar'},
]


@surucu_kursu_bp.route('/kursiyer/toplu/sablon')
@login_required
def kursiyer_toplu_sablon():
    """Toplu kursiyer yukleme Excel sablonunu indir."""
    _surucu_kursu_tenant_required()
    from app.toplu_yukleme import excel_sablonu_olustur
    from flask import send_file

    ehliyet_kodlari = ', '.join(kod for kod, _ in EHLIYET_SINIFLARI[:6]) + '…'
    aciklama = (
        'Zorunlu alanlar: Ad, Soyad, Ehliyet Sınıfı (kod). '
        f'Ehliyet kodları: {ehliyet_kodlari} (tüm liste için '
        'yeni kursiyer formundaki seçeneklere bakın). '
        'Telefon, ders sayısı, fiyat, eğitmen, kayıt tarihi opsiyoneldir. '
        'Eğitmen kullanıcı adı geçerli bir aktif öğretmen/yönetici olmalı; '
        'yoksa eğitmensiz kayıt yapılır.'
    )
    ornek = [
        ['Ali', 'Yılmaz', '12345678901', '0532 111 22 33', 'B_manuel',
         '32', '12500.00', 'ahmet_egitmen', '2026-05-01', 'Acemi sürücü'],
        ['Ayşe', 'Kaya', '', '0534 222 33 44', 'A2', '16', '7500.00',
         '', '', 'Hafta sonları'],
    ]
    output = excel_sablonu_olustur(
        KURSIYER_TOPLU_BASLIKLARI,
        ornek_satirlar=ornek,
        aciklama_satiri=aciklama,
        sayfa_adi='Kursiyerler',
    )
    return send_file(
        output, as_attachment=True,
        download_name='surucu_kursu_toplu_kursiyer_sablonu.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@surucu_kursu_bp.route('/kursiyer/toplu', methods=['GET', 'POST'])
@login_required
def kursiyer_toplu_yukle():
    """Toplu kursiyer yukleme: GET=form, POST=onizleme veya kaydet."""
    _surucu_kursu_tenant_required()
    onizleme = None
    hatalar_ozet = []

    if request.method == 'POST':
        eylem = request.form.get('eylem', 'onizle')

        if eylem == 'kaydet':
            # Onizlemeden gelen veriyi kaydet (form alanlari hidden olarak donmus)
            kayit_sayisi = _kursiyer_toplu_kaydet_post()
            if kayit_sayisi is None:
                # Hata flash icinde verildi
                return redirect(url_for('surucu_kursu.kursiyer_toplu_yukle'))
            flash(f'{kayit_sayisi} kursiyer başarıyla eklendi.', 'success')
            return redirect(url_for('surucu_kursu.kursiyer_liste'))

        # eylem == 'onizle' (default) — Excel'i parse et ve dogrula
        dosya = request.files.get('excel')
        if not dosya or not dosya.filename:
            flash('Lütfen bir Excel dosyası seçin.', 'danger')
            return redirect(url_for('surucu_kursu.kursiyer_toplu_yukle'))

        try:
            from app.toplu_yukleme import excel_oku
            satirlar = excel_oku(dosya, KURSIYER_TOPLU_BASLIKLARI)
        except Exception as e:
            flash(f'Excel okunamadı: {e}', 'danger')
            return redirect(url_for('surucu_kursu.kursiyer_toplu_yukle'))

        # Aktif egitmenleri username -> id map'le
        egitmenler = {
            u.username: u.id for u in User.query.filter(
                User.aktif.is_(True),
                User.rol.in_(['admin', 'yonetici', 'ogretmen']),
            ).all()
        }

        onizleme = []
        gecerli_sayi = 0
        hatalar_genel = 0
        for row in satirlar:
            satir = dict(row)
            satir['_hatalar'] = list(satir.get('_hatalar') or [])

            ad = (satir.get('ad') or '').strip() if satir.get('ad') else ''
            soyad = (satir.get('soyad') or '').strip() if satir.get('soyad') else ''
            sinif = (satir.get('ehliyet_sinifi') or '').strip() if satir.get('ehliyet_sinifi') else ''
            tc_raw = satir.get('tc_kimlik')
            tc = ''
            if tc_raw not in (None, ''):
                # Excel'den int olarak gelebilir
                tc = str(tc_raw).strip().replace('.0', '') if str(tc_raw).endswith('.0') else str(tc_raw).strip()

            if not ad:
                satir['_hatalar'].append('Ad zorunlu.')
            if not soyad:
                satir['_hatalar'].append('Soyad zorunlu.')
            if not sinif:
                satir['_hatalar'].append('Ehliyet sınıfı zorunlu.')
            elif sinif not in EHLIYET_SINIF_DICT:
                satir['_hatalar'].append(f'Geçersiz ehliyet kodu: {sinif!r}.')
            if tc:
                tc_ok, tc_hata = _tc_kimlik_dogrula(tc)
                if not tc_ok:
                    satir['_hatalar'].append(f'TC: {tc_hata}')

            # Sayisal alan dogrulamalari
            ders_raw = satir.get('ders_sayisi')
            if ders_raw not in (None, ''):
                if _int_or_none(ders_raw) is None:
                    satir['_hatalar'].append(f'Ders sayısı sayı olmalı: {ders_raw!r}.')

            fiyat_raw = satir.get('fiyat')
            if fiyat_raw not in (None, ''):
                if _decimal_or_none(fiyat_raw) is None:
                    satir['_hatalar'].append(f'Fiyat geçersiz: {fiyat_raw!r}.')

            tarih_raw = satir.get('kayit_tarihi')
            if tarih_raw not in (None, ''):
                # Excel datetime objesi de gelebilir
                if isinstance(tarih_raw, datetime):
                    pass
                elif isinstance(tarih_raw, date):
                    pass
                elif isinstance(tarih_raw, str) and _date_or_none(tarih_raw) is None:
                    satir['_hatalar'].append(f'Kayıt tarihi geçersiz: {tarih_raw!r} (YYYY-MM-DD).')

            egitmen_username = (satir.get('egitmen_username') or '').strip() if satir.get('egitmen_username') else ''
            if egitmen_username and egitmen_username not in egitmenler:
                satir['_hatalar'].append(f'Eğitmen bulunamadı: {egitmen_username!r}.')

            if satir['_hatalar']:
                hatalar_genel += 1
            else:
                gecerli_sayi += 1

            onizleme.append(satir)

        hatalar_ozet = {'gecerli': gecerli_sayi, 'hatali': hatalar_genel,
                        'toplam': len(onizleme)}

    return render_template(
        'surucu_kursu/kursiyer_toplu.html',
        onizleme=onizleme,
        hatalar_ozet=hatalar_ozet,
        ehliyet_dict=EHLIYET_SINIF_DICT,
    )


def _kursiyer_toplu_kaydet_post():
    """Onizleme sonrasi 'Kaydet' eylemi — form'dan hidden olarak gelen
    satirlari Kursiyer olarak insert et. Sadece hatasiz olanlar
    kaydedilir; hatalilar atlanir.

    Donus: kaydedilen sayi (None = hata).
    """
    egitmenler = {
        u.username: u.id for u in User.query.filter(
            User.aktif.is_(True),
            User.rol.in_(['admin', 'yonetici', 'ogretmen']),
        ).all()
    }

    indeksler = sorted({
        int(key.split('[')[1].rstrip(']'))
        for key in request.form.keys()
        if key.startswith('row_ad[')
    })
    if not indeksler:
        flash('Kaydedilecek satır yok.', 'warning')
        return None

    eklenen = 0
    for idx in indeksler:
        ad = (request.form.get(f'row_ad[{idx}]') or '').strip()
        soyad = (request.form.get(f'row_soyad[{idx}]') or '').strip()
        sinif = (request.form.get(f'row_ehliyet[{idx}]') or '').strip()
        if not ad or not soyad or sinif not in EHLIYET_SINIF_DICT:
            continue  # gecersiz, atla
        tc = (request.form.get(f'row_tc[{idx}]') or '').strip() or None
        if tc:
            tc_ok, _ = _tc_kimlik_dogrula(tc)
            if not tc_ok:
                tc = None  # gecersiz tc'yi sessizce dusur
        telefon = (request.form.get(f'row_telefon[{idx}]') or '').strip() or None
        ders_sayisi = _int_or_none(request.form.get(f'row_ders[{idx}]'))
        fiyat = _decimal_or_none(request.form.get(f'row_fiyat[{idx}]'))
        eg_username = (request.form.get(f'row_egitmen[{idx}]') or '').strip()
        eg_id = egitmenler.get(eg_username) if eg_username else None
        tarih = _date_or_none(request.form.get(f'row_tarih[{idx}]'))
        if tarih is None:
            tarih = date.today()
        notlar = (request.form.get(f'row_notlar[{idx}]') or '').strip() or None

        k = Kursiyer(
            ad=ad, soyad=soyad,
            tc_kimlik=tc,
            telefon=telefon,
            kayit_tarihi=tarih,
            ehliyet_sinifi=sinif,
            ders_sayisi=ders_sayisi,
            fiyat=fiyat or 0,
            egitmen_id=eg_id,
            notlar=notlar,
            aktif=True,
        )
        db.session.add(k)
        eklenen += 1

    db.session.commit()
    return eklenen


# === Kursiyer ek ehliyetleri (Faz 3.D) ===

def _kursiyer_fiyat_recalc(kursiyer):
    """Kursiyer.fiyat'i tum ehliyet (birincil + ek) fiyatlarinin
    toplami olarak yeniden hesapla. Ekle/duzenle/sil sonrasinda cagrilir.
    """
    toplam = Decimal('0')
    # Birincil ehliyet (eski akis - geriye uyumluluk)
    # NOTE: Yeni akista Kursiyer.fiyat zaten hep KursiyerEhliyet'lerden
    # geliyor. Eski kursiyerlerde Kursiyer.fiyat manuel girilmis olabilir;
    # eger ek_ehliyetler hic yoksa eski fiyati koru.
    eski_fiyatlar = [e.fiyat or Decimal('0') for e in kursiyer.ek_ehliyetler]
    if eski_fiyatlar:
        toplam = sum(eski_fiyatlar, Decimal('0'))
        kursiyer.fiyat = toplam


@surucu_kursu_bp.route(
    '/kursiyer/<int:kursiyer_id>/ehliyet-ekle', methods=['POST'])
@login_required
def kursiyer_ehliyet_ekle(kursiyer_id):
    """Kursiyere ehliyet ekle. Yeni akis: bu rota tum ehliyetleri
    yonetir (B + A2 + SRC vs.). Ayni kursiyerde ayni ehliyet 2 kez
    eklenemez (UNIQUE)."""
    _surucu_kursu_tenant_required()
    k = Kursiyer.query.get_or_404(kursiyer_id)

    sinif = (request.form.get('ehliyet_sinifi') or '').strip()
    ders_sayisi = _int_or_none(request.form.get('ders_sayisi'))
    fiyat = _decimal_or_none(request.form.get('fiyat'))
    egitmen_id = _int_or_none(request.form.get('egitmen_id'))
    notlar = (request.form.get('notlar') or '').strip()

    if sinif not in EHLIYET_SINIF_DICT:
        flash('Geçerli bir ehliyet sınıfı seçin.', 'danger')
        return redirect(url_for('surucu_kursu.kursiyer_detay',
                                 kursiyer_id=kursiyer_id))

    # Eski akista ehliyet_sinifi ile cakisma kontrolu (geriye uyum)
    if k.ehliyet_sinifi == sinif:
        flash('Bu ehliyet kursiyere zaten atanmış.', 'warning')
        return redirect(url_for('surucu_kursu.kursiyer_detay',
                                 kursiyer_id=kursiyer_id))

    mevcut = KursiyerEhliyet.query.filter_by(
        kursiyer_id=k.id, ehliyet_sinifi=sinif,
    ).first()
    if mevcut:
        flash('Bu ehliyet kursiyere zaten eklenmiş.', 'warning')
        return redirect(url_for('surucu_kursu.kursiyer_detay',
                                 kursiyer_id=kursiyer_id))

    e = KursiyerEhliyet(
        kursiyer_id=k.id,
        ehliyet_sinifi=sinif,
        ders_sayisi=ders_sayisi,
        fiyat=fiyat or 0,
        egitmen_id=egitmen_id,
        notlar=notlar or None,
        durum='aktif',
    )
    db.session.add(e)
    db.session.flush()
    _kursiyer_fiyat_recalc(k)
    db.session.commit()
    flash(f'"{EHLIYET_SINIF_DICT[sinif]}" ehliyeti eklendi.', 'success')
    return redirect(url_for('surucu_kursu.kursiyer_detay',
                             kursiyer_id=kursiyer_id))


@surucu_kursu_bp.route(
    '/kursiyer/<int:kursiyer_id>/ehliyet/<int:ehliyet_id>/duzenle',
    methods=['POST'])
@login_required
def kursiyer_ehliyet_duzenle(kursiyer_id, ehliyet_id):
    """Ehliyet fiyat/ders/egitmen/durum bilgisini guncelle."""
    _surucu_kursu_tenant_required()
    e = KursiyerEhliyet.query.filter_by(
        id=ehliyet_id, kursiyer_id=kursiyer_id
    ).first_or_404()

    e.ders_sayisi = _int_or_none(request.form.get('ders_sayisi'))
    e.fiyat = _decimal_or_none(request.form.get('fiyat')) or 0
    e.egitmen_id = _int_or_none(request.form.get('egitmen_id'))
    yeni_durum = (request.form.get('durum') or '').strip()
    if yeni_durum in ('aktif', 'tamamlandi', 'iptal'):
        e.durum = yeni_durum
    e.notlar = (request.form.get('notlar') or '').strip() or None

    _kursiyer_fiyat_recalc(e.kursiyer)
    db.session.commit()
    flash(f'"{e.ehliyet_sinifi_str}" ehliyeti güncellendi.', 'success')
    return redirect(url_for('surucu_kursu.kursiyer_detay',
                             kursiyer_id=kursiyer_id))


@surucu_kursu_bp.route(
    '/kursiyer/<int:kursiyer_id>/ehliyet/<int:ehliyet_id>/sil',
    methods=['POST'])
@login_required
def kursiyer_ehliyet_sil(kursiyer_id, ehliyet_id):
    """Ehliyeti sil."""
    _surucu_kursu_tenant_required()
    e = KursiyerEhliyet.query.filter_by(
        id=ehliyet_id, kursiyer_id=kursiyer_id
    ).first_or_404()
    sinif_str = e.ehliyet_sinifi_str
    kursiyer = e.kursiyer
    db.session.delete(e)
    db.session.flush()
    _kursiyer_fiyat_recalc(kursiyer)
    db.session.commit()
    flash(f'"{sinif_str}" ehliyeti silindi.', 'info')
    return redirect(url_for('surucu_kursu.kursiyer_detay',
                             kursiyer_id=kursiyer_id))

# === Yonlendirme komisyon -> Muhasebe otomatik baglanti ===

YONLENDIRME_KOMISYON_KATEGORI_ADI = 'Yönlendirme Komisyonu'


def _yonlendirme_komisyon_kategorisi_getir():
    kat = GelirGiderKategorisi.query.filter_by(
        ad=YONLENDIRME_KOMISYON_KATEGORI_ADI, tur='gelir',
    ).first()
    if kat is None:
        kat = GelirGiderKategorisi(
            ad=YONLENDIRME_KOMISYON_KATEGORI_ADI, tur='gelir', aktif=True,
        )
        db.session.add(kat)
        db.session.flush()
    return kat


def _yonlendirme_komisyon_gelir_olustur(yonl):
    """Komisyon alindi olarak isaretlendiginde gelir kaydi olustur."""
    if yonl.gelir_gider_kayit_id:
        return None
    if not yonl.komisyon_tutari or yonl.komisyon_tutari <= 0:
        return None
    kat = _yonlendirme_komisyon_kategorisi_getir()
    aciklama = (
        f'{yonl.kursiyer.tam_ad} — {yonl.ehliyet_sinifi_str} '
        f'yönlendirme komisyonu ({yonl.hedef_kurs_adi})'
    )
    kayit = GelirGiderKaydi(
        tur='gelir',
        kategori_id=kat.id,
        tutar=yonl.komisyon_tutari,
        aciklama=aciklama,
        tarih=yonl.komisyon_tarihi or date.today(),
        belge_no=f'YK-{yonl.id}',
        banka_hesap_id=None,
        olusturan_id=current_user.id,
    )
    db.session.add(kayit)
    db.session.flush()
    yonl.gelir_gider_kayit_id = kayit.id
    return kayit


def _yonlendirme_komisyon_gelir_temizle(yonl):
    if not yonl.gelir_gider_kayit_id:
        return
    kayit = GelirGiderKaydi.query.filter_by(
        id=yonl.gelir_gider_kayit_id,
    ).first()
    if kayit:
        db.session.delete(kayit)
    yonl.gelir_gider_kayit_id = None


# === Yonlendirme route'lari ===

@surucu_kursu_bp.route('/yonlendirmeler')
@login_required
def yonlendirme_liste():
    """Tum yonlendirmeleri listele - filtreli."""
    _surucu_kursu_tenant_required()

    durum = (request.args.get('durum') or '').strip()
    arama = (request.args.get('arama') or '').strip()

    q = KursiyerYonlendirme.query.join(Kursiyer)
    if durum:
        q = q.filter(KursiyerYonlendirme.durum == durum)
    if arama:
        like = f'%{arama}%'
        q = q.filter(or_(
            Kursiyer.ad.ilike(like),
            Kursiyer.soyad.ilike(like),
            KursiyerYonlendirme.hedef_kurs_adi.ilike(like),
        ))
    yonlendirmeler = q.order_by(
        KursiyerYonlendirme.yonlendirme_tarihi.desc()
    ).limit(500).all()

    # Ozet (toplam komisyon, alinan, alinmayan)
    toplam = sum((y.komisyon_tutari or Decimal('0'))
                 for y in yonlendirmeler)
    alinan = sum((y.komisyon_tutari or Decimal('0'))
                 for y in yonlendirmeler if y.komisyon_alindi_mi)
    bekleyen = toplam - alinan

    return render_template(
        'surucu_kursu/yonlendirme_liste.html',
        yonlendirmeler=yonlendirmeler,
        durum=durum, arama=arama,
        durumlar=KursiyerYonlendirme.DURUMLAR,
        ehliyet_dict=EHLIYET_SINIF_DICT,
        toplam_komisyon=toplam,
        alinan_komisyon=alinan,
        bekleyen_komisyon=bekleyen,
    )


@surucu_kursu_bp.route(
    '/kursiyer/<int:kursiyer_id>/yonlendirme/ekle',
    methods=['POST'])
@login_required
def yonlendirme_ekle(kursiyer_id):
    _surucu_kursu_tenant_required()
    k = Kursiyer.query.get_or_404(kursiyer_id)

    ehliyet_sinifi = (request.form.get('ehliyet_sinifi') or '').strip()
    hedef_kurs_adi = (request.form.get('hedef_kurs_adi') or '').strip()
    hedef_kurs_telefon = (request.form.get('hedef_kurs_telefon') or '').strip()
    hedef_kurs_yetkili = (request.form.get('hedef_kurs_yetkili') or '').strip()
    yonl_tarihi = _date_or_none(request.form.get('yonlendirme_tarihi')) \
        or date.today()
    komisyon = _decimal_or_none(request.form.get('komisyon_tutari')) \
        or Decimal('0')
    durum = (request.form.get('durum') or 'yonlendirildi').strip()
    notlar = (request.form.get('notlar') or '').strip()

    if not ehliyet_sinifi or ehliyet_sinifi not in EHLIYET_SINIF_DICT:
        flash('Geçerli bir ehliyet sınıfı seçin.', 'danger')
        return redirect(url_for('surucu_kursu.kursiyer_detay',
                                 kursiyer_id=k.id))
    if not hedef_kurs_adi:
        flash('Hedef kursun adı zorunludur.', 'danger')
        return redirect(url_for('surucu_kursu.kursiyer_detay',
                                 kursiyer_id=k.id))
    if durum not in dict(KursiyerYonlendirme.DURUMLAR):
        durum = 'yonlendirildi'

    y = KursiyerYonlendirme(
        kursiyer_id=k.id,
        ehliyet_sinifi=ehliyet_sinifi,
        hedef_kurs_adi=hedef_kurs_adi,
        hedef_kurs_telefon=hedef_kurs_telefon or None,
        hedef_kurs_yetkili=hedef_kurs_yetkili or None,
        yonlendiren_id=current_user.id,
        yonlendirme_tarihi=yonl_tarihi,
        komisyon_tutari=komisyon,
        komisyon_alindi_mi=False,
        durum=durum,
        notlar=notlar or None,
    )
    db.session.add(y)
    db.session.commit()
    flash(f'Yönlendirme kaydedildi: {hedef_kurs_adi} '
          f'({y.ehliyet_sinifi_str}).', 'success')
    return redirect(url_for('surucu_kursu.kursiyer_detay',
                             kursiyer_id=k.id))


@surucu_kursu_bp.route(
    '/kursiyer/<int:kursiyer_id>/yonlendirme/<int:yonl_id>/duzenle',
    methods=['POST'])
@login_required
def yonlendirme_duzenle(kursiyer_id, yonl_id):
    _surucu_kursu_tenant_required()
    y = KursiyerYonlendirme.query.filter_by(
        id=yonl_id, kursiyer_id=kursiyer_id
    ).first_or_404()

    ehliyet_sinifi = (request.form.get('ehliyet_sinifi') or '').strip()
    hedef_kurs_adi = (request.form.get('hedef_kurs_adi') or '').strip()
    hedef_kurs_telefon = (request.form.get('hedef_kurs_telefon') or '').strip()
    hedef_kurs_yetkili = (request.form.get('hedef_kurs_yetkili') or '').strip()
    yonl_tarihi = _date_or_none(request.form.get('yonlendirme_tarihi'))
    yeni_komisyon = _decimal_or_none(request.form.get('komisyon_tutari')) \
        or Decimal('0')
    durum = (request.form.get('durum') or '').strip()
    notlar = (request.form.get('notlar') or '').strip()

    if ehliyet_sinifi and ehliyet_sinifi in EHLIYET_SINIF_DICT:
        y.ehliyet_sinifi = ehliyet_sinifi
    if hedef_kurs_adi:
        y.hedef_kurs_adi = hedef_kurs_adi
    y.hedef_kurs_telefon = hedef_kurs_telefon or None
    y.hedef_kurs_yetkili = hedef_kurs_yetkili or None
    if yonl_tarihi:
        y.yonlendirme_tarihi = yonl_tarihi
    if durum in dict(KursiyerYonlendirme.DURUMLAR):
        y.durum = durum
    y.notlar = notlar or None

    # Komisyon tutari degistiyse, eger gelir kaydi varsa senkronize et
    if y.komisyon_alindi_mi and y.gelir_gider_kayit_id and \
            yeni_komisyon != (y.komisyon_tutari or Decimal('0')):
        # Eski kaydi sil + yenisini olustur
        _yonlendirme_komisyon_gelir_temizle(y)
        y.komisyon_tutari = yeni_komisyon
        if yeni_komisyon > 0:
            _yonlendirme_komisyon_gelir_olustur(y)
        else:
            y.komisyon_alindi_mi = False
            y.komisyon_tarihi = None
    else:
        y.komisyon_tutari = yeni_komisyon

    db.session.commit()
    flash('Yönlendirme güncellendi.', 'success')
    return redirect(url_for('surucu_kursu.kursiyer_detay',
                             kursiyer_id=kursiyer_id))


@surucu_kursu_bp.route(
    '/kursiyer/<int:kursiyer_id>/yonlendirme/<int:yonl_id>/komisyon-tahsil',
    methods=['POST'])
@login_required
def yonlendirme_komisyon_tahsil(kursiyer_id, yonl_id):
    """Komisyon alindi olarak isaretle ve gelir kaydi olustur."""
    _surucu_kursu_tenant_required()
    y = KursiyerYonlendirme.query.filter_by(
        id=yonl_id, kursiyer_id=kursiyer_id
    ).first_or_404()
    if y.komisyon_alindi_mi:
        flash('Bu yönlendirmenin komisyonu zaten tahsil edilmiş.', 'info')
        return redirect(url_for('surucu_kursu.kursiyer_detay',
                                 kursiyer_id=kursiyer_id))
    if not y.komisyon_tutari or y.komisyon_tutari <= 0:
        flash('Komisyon tutarı belirtilmemiş.', 'warning')
        return redirect(url_for('surucu_kursu.kursiyer_detay',
                                 kursiyer_id=kursiyer_id))

    tarih = _date_or_none(request.form.get('komisyon_tarihi')) or date.today()
    y.komisyon_alindi_mi = True
    y.komisyon_tarihi = tarih
    _yonlendirme_komisyon_gelir_olustur(y)
    db.session.commit()
    flash(f'Komisyon tahsil edildi: {y.komisyon_tutari} ₺ '
          f'(gelir kaydı oluşturuldu).', 'success')
    return redirect(url_for('surucu_kursu.kursiyer_detay',
                             kursiyer_id=kursiyer_id))


@surucu_kursu_bp.route(
    '/kursiyer/<int:kursiyer_id>/yonlendirme/<int:yonl_id>/komisyon-iptal',
    methods=['POST'])
@login_required
def yonlendirme_komisyon_iptal(kursiyer_id, yonl_id):
    """Komisyon tahsilini geri al — gelir kaydini sil."""
    _surucu_kursu_tenant_required()
    y = KursiyerYonlendirme.query.filter_by(
        id=yonl_id, kursiyer_id=kursiyer_id
    ).first_or_404()
    if not y.komisyon_alindi_mi:
        flash('Bu komisyon zaten tahsil edilmemiş.', 'info')
        return redirect(url_for('surucu_kursu.kursiyer_detay',
                                 kursiyer_id=kursiyer_id))
    _yonlendirme_komisyon_gelir_temizle(y)
    y.komisyon_alindi_mi = False
    y.komisyon_tarihi = None
    db.session.commit()
    flash('Komisyon tahsili iptal edildi.', 'info')
    return redirect(url_for('surucu_kursu.kursiyer_detay',
                             kursiyer_id=kursiyer_id))


@surucu_kursu_bp.route(
    '/kursiyer/<int:kursiyer_id>/yonlendirme/<int:yonl_id>/sil',
    methods=['POST'])
@login_required
def yonlendirme_sil(kursiyer_id, yonl_id):
    _surucu_kursu_tenant_required()
    y = KursiyerYonlendirme.query.filter_by(
        id=yonl_id, kursiyer_id=kursiyer_id
    ).first_or_404()
    # Bagli gelir kaydi varsa once temizle
    _yonlendirme_komisyon_gelir_temizle(y)
    hedef = y.hedef_kurs_adi
    db.session.delete(y)
    db.session.commit()
    flash(f'"{hedef}" yönlendirme kaydı silindi.', 'info')
    return redirect(url_for('surucu_kursu.kursiyer_detay',
                             kursiyer_id=kursiyer_id))


# === Yetkilendirme (sadece surucu kursu modulleri icin sade UI) ===

# Surucu kursu yonetim sayfasi - sadece bu rolleri gosterir
SURUCU_KURSU_ROLLERI = [
    ('admin',      'Sistem Yöneticisi'),
    ('yonetici',   'Kurs Yöneticisi'),
    ('ogretmen',   'Eğitmen'),
    ('muhasebeci', 'Muhasebeci'),
]


def _admin_veya_yonetici_required():
    """Sadece admin/yonetici erissin - yetkilendirmeyi onlar yapar."""
    if not current_user.is_authenticated:
        abort(401)
    if current_user.rol not in ('admin', 'yonetici'):
        abort(403)


@surucu_kursu_bp.route('/ayarlar/yetkilendirme', methods=['GET', 'POST'])
@login_required
def yetkilendirme():
    """Surucu kursu modulleri icin rol-bazli izin matrisi.
    Yonetici diger rollerin (egitmen, muhasebeci) hangi modulleri
    gorebilecegini bu sayfadan ayarlar.
    """
    _surucu_kursu_tenant_required()
    _admin_veya_yonetici_required()

    from app.models.ayarlar import RolModulIzin

    moduller = [
        (k, RolModulIzin.MODULLER[k])
        for k in RolModulIzin.SURUCU_KURSU_MODUL_KEYLERI
        if k in RolModulIzin.MODULLER
    ]
    roller = SURUCU_KURSU_ROLLERI

    if request.method == 'POST':
        # admin daima tum modulleri gorur — formdan gelse bile zorla True
        for rol_kod, _ in roller:
            for modul_key, _ in moduller:
                aktif = (rol_kod == 'admin') or \
                    (f'izin_{rol_kod}_{modul_key}' in request.form)
                izin = RolModulIzin.query.filter_by(
                    rol=rol_kod, modul_key=modul_key
                ).first()
                if izin:
                    izin.aktif = aktif
                else:
                    db.session.add(RolModulIzin(
                        rol=rol_kod, modul_key=modul_key, aktif=aktif,
                    ))
        db.session.commit()
        flash('Yetkilendirme ayarları kaydedildi.', 'success')
        return redirect(url_for('surucu_kursu.yetkilendirme'))

    # GET: mevcut durumu hazirla
    izinler = {}
    for rol_kod, _ in roller:
        izinler[rol_kod] = {}
        for modul_key, _ in moduller:
            iz = RolModulIzin.query.filter_by(
                rol=rol_kod, modul_key=modul_key
            ).first()
            # admin varsayilan olarak hep aktif; digerleri kayit yoksa pasif
            if iz is None:
                izinler[rol_kod][modul_key] = (rol_kod == 'admin')
            else:
                izinler[rol_kod][modul_key] = iz.aktif

    return render_template(
        'surucu_kursu/yetkilendirme.html',
        roller=roller,
        moduller=moduller,
        izinler=izinler,
    )


# === Makbuz arama ===

@surucu_kursu_bp.route('/makbuz')
@login_required
def makbuz_arama():
    """Makbuz numarasi / kursiyer adi ile makbuzlari ara.

    Iki tip makbuz var:
        - KSR-... : Kursiyer egitim ucreti taksiti makbuzu
        - SHR-... : Sinav harc tahsilat makbuzu

    - Birebir makbuz no eslesirse direkt makbuz sayfasina 302
    - Aksi halde her iki tip de partial match ile listelenir
    """
    _surucu_kursu_tenant_required()

    q = (request.args.get('q') or '').strip()

    # Birebir makbuz eslesmesi - tip prefixine gore yonlendir
    if q:
        # Once kursiyer taksiti
        tam_eslesme = KursiyerTaksit.query.filter(
            KursiyerTaksit.makbuz_no == q,
            KursiyerTaksit.odendi_mi.is_(True),
        ).first()
        if tam_eslesme:
            return redirect(url_for(
                'surucu_kursu.taksit_makbuz',
                kursiyer_id=tam_eslesme.kursiyer_id,
                taksit_id=tam_eslesme.id,
            ))
        # Sonra sinav harc
        sh_eslesme = SurucuSinavHarciKaydi.query.filter(
            SurucuSinavHarciKaydi.makbuz_no == q,
            SurucuSinavHarciKaydi.durum == 'tahsil_edildi',
        ).first()
        if sh_eslesme:
            return redirect(url_for(
                'surucu_kursu.sinav_harc_makbuz',
                oturum_id=sh_eslesme.sinav_oturum_id,
                harc_id=sh_eslesme.id,
            ))

    # Liste sorgusu - kursiyer taksitleri
    qs = KursiyerTaksit.query.join(Kursiyer).filter(
        KursiyerTaksit.odendi_mi.is_(True),
        KursiyerTaksit.makbuz_no.isnot(None),
    )
    if q:
        like = f'%{q}%'
        qs = qs.filter(or_(
            KursiyerTaksit.makbuz_no.ilike(like),
            Kursiyer.ad.ilike(like),
            Kursiyer.soyad.ilike(like),
            KursiyerTaksit.odeyen_ad.ilike(like),
        ))
    taksit_makbuzlari = qs.order_by(KursiyerTaksit.odeme_tarihi.desc(),
                                     KursiyerTaksit.id.desc()).limit(200).all()

    # Liste sorgusu - sinav harc
    qs2 = SurucuSinavHarciKaydi.query.join(Kursiyer).filter(
        SurucuSinavHarciKaydi.durum == 'tahsil_edildi',
        SurucuSinavHarciKaydi.makbuz_no.isnot(None),
    )
    if q:
        like = f'%{q}%'
        qs2 = qs2.filter(or_(
            SurucuSinavHarciKaydi.makbuz_no.ilike(like),
            Kursiyer.ad.ilike(like),
            Kursiyer.soyad.ilike(like),
            SurucuSinavHarciKaydi.odeyen_ad.ilike(like),
        ))
    sh_makbuzlari = qs2.order_by(
        SurucuSinavHarciKaydi.tahsil_tarihi.desc(),
        SurucuSinavHarciKaydi.id.desc()
    ).limit(200).all()

    # Birlestirilmis liste - tek formatta render edilebilsin
    items = []
    for t in taksit_makbuzlari:
        items.append({
            'tip': 'taksit',
            'makbuz_no': t.makbuz_no,
            'tarih': t.odeme_tarihi,
            'kursiyer': t.kursiyer,
            'kursiyer_id': t.kursiyer_id,
            'aciklama': f'{t.sira}. taksit',
            'odeyen_ad': t.odeyen_ad,
            'tutar': t.tutar,
            'odeme_turu': t.odeme_turu,
            'odeme_turu_str': t.odeme_turu_str,
            'makbuz_url': url_for('surucu_kursu.taksit_makbuz',
                                    kursiyer_id=t.kursiyer_id,
                                    taksit_id=t.id),
        })
    for h in sh_makbuzlari:
        items.append({
            'tip': 'sinav_harc',
            'makbuz_no': h.makbuz_no,
            'tarih': h.tahsil_tarihi,
            'kursiyer': h.kursiyer,
            'kursiyer_id': h.kursiyer_id,
            'aciklama': f'Sınav harcı ({h.sinav_oturum.sinav_tipi_str})',
            'odeyen_ad': h.odeyen_ad,
            'tutar': h.ucret,
            'odeme_turu': h.odeme_turu,
            'odeme_turu_str': h.odeme_turu_str,
            'makbuz_url': url_for('surucu_kursu.sinav_harc_makbuz',
                                    oturum_id=h.sinav_oturum_id,
                                    harc_id=h.id),
        })
    # Tarihe gore birlestirilmis sirala (yeniden eskiye)
    items.sort(key=lambda x: (x['tarih'] or date.min), reverse=True)
    items = items[:200]

    return render_template(
        'surucu_kursu/makbuz_liste.html',
        makbuzlar=items, q=q,
    )


# === Donemler (ay bazli kursiyer gruplama) ===

@surucu_kursu_bp.route('/donem/')
@login_required
def donem_liste():
    """Tum donemler — her donem icin kursiyer sayisi + odeme ozeti."""
    _surucu_kursu_tenant_required()

    durum = (request.args.get('durum') or '').strip()
    qs = Donem.query
    if durum in ('aktif', 'kapali'):
        qs = qs.filter(Donem.durum == durum)
    donemler = qs.order_by(Donem.yil.desc(), Donem.ay.desc()).all()

    # Her donem icin: kursiyer sayisi, fiyat toplami, tahsilat toplami,
    # bekleyen taksit toplami (tek seferlik aggregate)
    donem_id_to_stat = {}
    if donemler:
        ids = [d.id for d in donemler]
        # Kursiyer sayisi + fiyat toplami
        rows = db.session.query(
            Kursiyer.donem_id,
            func.count(Kursiyer.id),
            func.coalesce(func.sum(Kursiyer.fiyat), 0),
        ).filter(
            Kursiyer.donem_id.in_(ids),
            Kursiyer.aktif.is_(True),
        ).group_by(Kursiyer.donem_id).all()
        for did, sayi, fiyat in rows:
            donem_id_to_stat[did] = {
                'kursiyer_sayisi': sayi,
                'toplam_fiyat': fiyat or Decimal('0'),
                'odenen': Decimal('0'),
                'kalan': Decimal('0'),
            }
        # Odenen taksit toplami (donem bazli)
        rows2 = db.session.query(
            Kursiyer.donem_id,
            func.coalesce(func.sum(KursiyerTaksit.tutar), 0),
        ).join(KursiyerTaksit, KursiyerTaksit.kursiyer_id == Kursiyer.id).filter(
            Kursiyer.donem_id.in_(ids),
            KursiyerTaksit.odendi_mi.is_(True),
        ).group_by(Kursiyer.donem_id).all()
        for did, odenen in rows2:
            if did in donem_id_to_stat:
                donem_id_to_stat[did]['odenen'] = odenen or Decimal('0')
        # Kalan = toplam_fiyat - odenen
        for did, st in donem_id_to_stat.items():
            st['kalan'] = (st['toplam_fiyat'] or Decimal('0')) - \
                          (st['odenen'] or Decimal('0'))

    return render_template(
        'surucu_kursu/donem_liste.html',
        donemler=donemler,
        donem_stat=donem_id_to_stat,
        durum=durum,
    )


@surucu_kursu_bp.route('/donem/<int:donem_id>')
@login_required
def donem_detay(donem_id):
    """Bir donemin detayi — o donemdeki kursiyerler + odeme tablosu."""
    _surucu_kursu_tenant_required()
    d = Donem.query.get_or_404(donem_id)

    kursiyerler = Kursiyer.query.filter_by(
        donem_id=d.id, aktif=True
    ).order_by(Kursiyer.ad, Kursiyer.soyad).all()

    # Her kursiyer icin odeme ozeti
    kursiyer_ozet = []
    toplam_fiyat = Decimal('0')
    toplam_odenen = Decimal('0')
    for k in kursiyerler:
        odenen = sum(
            (t.tutar or Decimal('0'))
            for t in k.taksitler if t.odendi_mi
        ) or Decimal('0')
        toplam = k.fiyat or Decimal('0')
        kalan = toplam - odenen
        kursiyer_ozet.append({
            'k': k,
            'toplam': toplam,
            'odenen': odenen,
            'kalan': kalan,
            'oran': int((odenen / toplam * 100) if toplam else 0),
        })
        toplam_fiyat += toplam
        toplam_odenen += odenen

    return render_template(
        'surucu_kursu/donem_detay.html',
        donem=d,
        kursiyer_ozet=kursiyer_ozet,
        toplam_fiyat=toplam_fiyat,
        toplam_odenen=toplam_odenen,
        toplam_kalan=toplam_fiyat - toplam_odenen,
        ehliyet_dict=EHLIYET_SINIF_DICT,
    )


@surucu_kursu_bp.route('/donem/yeni', methods=['POST'])
@login_required
def donem_yeni():
    """Manuel donem olustur (genelde otomatik olusur, manuel
    onceden ay acilmasi icin)."""
    _surucu_kursu_tenant_required()
    try:
        yil = int(request.form.get('yil') or 0)
        ay = int(request.form.get('ay') or 0)
    except ValueError:
        flash('Geçersiz yıl/ay.', 'danger')
        return redirect(url_for('surucu_kursu.donem_liste'))
    if yil < 2000 or yil > 2100 or ay < 1 or ay > 12:
        flash('Yıl 2000-2100, ay 1-12 olmalı.', 'danger')
        return redirect(url_for('surucu_kursu.donem_liste'))

    mevcut = Donem.query.filter_by(yil=yil, ay=ay).first()
    if mevcut:
        flash(f'{mevcut.ad} dönemi zaten mevcut.', 'info')
        return redirect(url_for('surucu_kursu.donem_detay',
                                 donem_id=mevcut.id))
    d = Donem.from_yil_ay(yil, ay)
    aciklama = (request.form.get('aciklama') or '').strip()
    if aciklama:
        d.aciklama = aciklama
    db.session.add(d)
    db.session.commit()
    flash(f'{d.ad} dönemi oluşturuldu.', 'success')
    return redirect(url_for('surucu_kursu.donem_detay', donem_id=d.id))


@surucu_kursu_bp.route('/donem/<int:donem_id>/duzenle', methods=['POST'])
@login_required
def donem_duzenle(donem_id):
    """Donem aciklama/durum guncelleme."""
    _surucu_kursu_tenant_required()
    d = Donem.query.get_or_404(donem_id)

    durum = (request.form.get('durum') or '').strip()
    aciklama = (request.form.get('aciklama') or '').strip()

    if durum in ('aktif', 'kapali'):
        d.durum = durum
    d.aciklama = aciklama or None
    db.session.commit()
    flash(f'{d.ad} dönemi güncellendi.', 'success')
    return redirect(url_for('surucu_kursu.donem_detay', donem_id=d.id))


@surucu_kursu_bp.route('/donem/<int:donem_id>/sil', methods=['POST'])
@login_required
def donem_sil(donem_id):
    """Donem silme — sadece bos donemler silinebilir."""
    _surucu_kursu_tenant_required()
    d = Donem.query.get_or_404(donem_id)
    kursiyer_sayisi = Kursiyer.query.filter_by(donem_id=d.id).count()
    if kursiyer_sayisi > 0:
        flash(f'{d.ad} dönemine bağlı {kursiyer_sayisi} kursiyer var. '
              f'Önce kursiyerleri başka döneme taşıyın veya silin.',
              'warning')
        return redirect(url_for('surucu_kursu.donem_detay',
                                 donem_id=d.id))
    ad = d.ad
    db.session.delete(d)
    db.session.commit()
    flash(f'{ad} dönemi silindi.', 'info')
    return redirect(url_for('surucu_kursu.donem_liste'))


# === Komisyon Odemeleri (BIZE yonlendirilenler -> bizim ödeyecegimiz) ===

KOMISYON_GIDERI_KATEGORI_ADI = 'Yönlendirme Komisyon Gideri'


def _komisyon_gideri_kategorisi_getir():
    kat = GelirGiderKategorisi.query.filter_by(
        ad=KOMISYON_GIDERI_KATEGORI_ADI, tur='gider',
    ).first()
    if kat is None:
        kat = GelirGiderKategorisi(
            ad=KOMISYON_GIDERI_KATEGORI_ADI, tur='gider', aktif=True,
        )
        db.session.add(kat)
        db.session.flush()
    return kat


def _komisyon_gider_olustur(k):
    """Komisyon odendi olarak isaretlendiginde otomatik gider kaydi
    olustur. Idempotent."""
    if k.gelir_gider_kayit_id:
        return None
    if not k.komisyon_tutari or k.komisyon_tutari <= 0:
        return None
    kat = _komisyon_gideri_kategorisi_getir()
    aciklama = (
        f'{k.kursiyer_adi} — {k.ehliyet_sinifi_str} yönlendirme '
        f'komisyonu (kaynak: {k.kaynak_kurs_adi})'
    )
    kayit = GelirGiderKaydi(
        tur='gider',
        kategori_id=kat.id,
        tutar=k.komisyon_tutari,
        aciklama=aciklama,
        tarih=k.odeme_tarihi or date.today(),
        belge_no=f'KMSY-{k.id}',
        banka_hesap_id=None,
        olusturan_id=current_user.id,
    )
    db.session.add(kayit)
    db.session.flush()
    k.gelir_gider_kayit_id = kayit.id
    return kayit


def _komisyon_gider_temizle(k):
    if not k.gelir_gider_kayit_id:
        return
    kayit = GelirGiderKaydi.query.filter_by(
        id=k.gelir_gider_kayit_id,
    ).first()
    if kayit:
        db.session.delete(kayit)
    k.gelir_gider_kayit_id = None


@surucu_kursu_bp.route('/komisyon/')
@login_required
def komisyon_liste():
    """Bize yonlendirilen kursiyerler icin odenecek/odenen komisyonlar."""
    _surucu_kursu_tenant_required()

    durum = (request.args.get('durum') or '').strip()
    arama = (request.args.get('arama') or '').strip()

    q = KomisyonOdemesi.query
    if durum == 'odendi':
        q = q.filter(KomisyonOdemesi.odendi_mi.is_(True))
    elif durum == 'bekliyor':
        q = q.filter(KomisyonOdemesi.odendi_mi.is_(False))
    if arama:
        like = f'%{arama}%'
        q = q.filter(or_(
            KomisyonOdemesi.kursiyer_adi.ilike(like),
            KomisyonOdemesi.kaynak_kurs_adi.ilike(like),
            KomisyonOdemesi.kaynak_kurs_yetkili.ilike(like),
        ))
    komisyonlar = q.order_by(
        KomisyonOdemesi.yonlendirme_tarihi.desc(),
        KomisyonOdemesi.id.desc()
    ).limit(500).all()

    toplam = sum((k.komisyon_tutari or Decimal('0')) for k in komisyonlar)
    odenen = sum((k.komisyon_tutari or Decimal('0'))
                 for k in komisyonlar if k.odendi_mi)
    bekleyen = toplam - odenen

    # Kursiyer secici (formda)
    kursiyer_listesi = Kursiyer.query.filter(
        Kursiyer.aktif.is_(True)
    ).order_by(Kursiyer.ad, Kursiyer.soyad).all()

    return render_template(
        'surucu_kursu/komisyon_liste.html',
        komisyonlar=komisyonlar,
        kursiyer_listesi=kursiyer_listesi,
        ehliyet_siniflari=EHLIYET_SINIFLARI,
        durum=durum, arama=arama,
        toplam=toplam, odenen=odenen, bekleyen=bekleyen,
        bugun=date.today(),
    )


@surucu_kursu_bp.route('/komisyon/yeni', methods=['POST'])
@login_required
def komisyon_yeni():
    _surucu_kursu_tenant_required()

    kursiyer_id = _int_or_none(request.form.get('kursiyer_id'))
    kursiyer_adi = (request.form.get('kursiyer_adi') or '').strip()
    if kursiyer_id:
        k_obj = Kursiyer.query.get(kursiyer_id)
        if k_obj:
            kursiyer_adi = k_obj.tam_ad
        else:
            kursiyer_id = None
    if not kursiyer_adi:
        flash('Kursiyer adı zorunludur.', 'danger')
        return redirect(url_for('surucu_kursu.komisyon_liste'))

    kursiyer_telefon = (request.form.get('kursiyer_telefon') or '').strip()
    ehliyet_sinifi = (request.form.get('ehliyet_sinifi') or '').strip()
    if ehliyet_sinifi and ehliyet_sinifi not in EHLIYET_SINIF_DICT:
        ehliyet_sinifi = None
    kaynak_kurs_adi = (request.form.get('kaynak_kurs_adi') or '').strip()
    kaynak_kurs_yetkili = (request.form.get('kaynak_kurs_yetkili') or '').strip()
    kaynak_kurs_telefon = (request.form.get('kaynak_kurs_telefon') or '').strip()
    yonl_tarihi = _date_or_none(request.form.get('yonlendirme_tarihi')) \
        or date.today()
    komisyon = _decimal_or_none(request.form.get('komisyon_tutari')) \
        or Decimal('0')
    aciklama = (request.form.get('aciklama') or '').strip()

    if not kaynak_kurs_adi:
        flash('Kaynak kurs adı zorunludur.', 'danger')
        return redirect(url_for('surucu_kursu.komisyon_liste'))

    k = KomisyonOdemesi(
        kursiyer_id=kursiyer_id,
        kursiyer_adi=kursiyer_adi,
        kursiyer_telefon=kursiyer_telefon or None,
        ehliyet_sinifi=ehliyet_sinifi or None,
        kaynak_kurs_adi=kaynak_kurs_adi,
        kaynak_kurs_yetkili=kaynak_kurs_yetkili or None,
        kaynak_kurs_telefon=kaynak_kurs_telefon or None,
        kaydeden_id=current_user.id,
        yonlendirme_tarihi=yonl_tarihi,
        komisyon_tutari=komisyon,
        odendi_mi=False,
        aciklama=aciklama or None,
    )
    db.session.add(k)
    db.session.commit()
    flash(f'Komisyon kaydedildi: {kaynak_kurs_adi} → {kursiyer_adi} '
          f'({komisyon} ₺).', 'success')
    return redirect(url_for('surucu_kursu.komisyon_liste'))


@surucu_kursu_bp.route('/komisyon/<int:komisyon_id>/duzenle', methods=['POST'])
@login_required
def komisyon_duzenle(komisyon_id):
    _surucu_kursu_tenant_required()
    k = KomisyonOdemesi.query.get_or_404(komisyon_id)

    kursiyer_adi = (request.form.get('kursiyer_adi') or '').strip()
    if kursiyer_adi:
        k.kursiyer_adi = kursiyer_adi
    k.kursiyer_telefon = (request.form.get('kursiyer_telefon') or '').strip() or None
    yeni_ehl = (request.form.get('ehliyet_sinifi') or '').strip()
    k.ehliyet_sinifi = yeni_ehl if yeni_ehl in EHLIYET_SINIF_DICT else None
    yeni_kaynak = (request.form.get('kaynak_kurs_adi') or '').strip()
    if yeni_kaynak:
        k.kaynak_kurs_adi = yeni_kaynak
    k.kaynak_kurs_yetkili = (request.form.get('kaynak_kurs_yetkili') or '').strip() or None
    k.kaynak_kurs_telefon = (request.form.get('kaynak_kurs_telefon') or '').strip() or None
    yt = _date_or_none(request.form.get('yonlendirme_tarihi'))
    if yt:
        k.yonlendirme_tarihi = yt
    yeni_komisyon = _decimal_or_none(request.form.get('komisyon_tutari')) \
        or Decimal('0')

    # Eger zaten odendi ise ve tutar degistiyse gider kaydini senkronize et
    if k.odendi_mi and k.gelir_gider_kayit_id and \
            yeni_komisyon != (k.komisyon_tutari or Decimal('0')):
        _komisyon_gider_temizle(k)
        k.komisyon_tutari = yeni_komisyon
        if yeni_komisyon > 0:
            _komisyon_gider_olustur(k)
        else:
            k.odendi_mi = False
            k.odeme_tarihi = None
    else:
        k.komisyon_tutari = yeni_komisyon

    k.aciklama = (request.form.get('aciklama') or '').strip() or None
    db.session.commit()
    flash('Komisyon güncellendi.', 'success')
    return redirect(url_for('surucu_kursu.komisyon_liste'))


@surucu_kursu_bp.route('/komisyon/<int:komisyon_id>/odeme', methods=['POST'])
@login_required
def komisyon_odeme(komisyon_id):
    """Komisyonu odendi olarak isaretle ve gider kaydi olustur."""
    _surucu_kursu_tenant_required()
    k = KomisyonOdemesi.query.get_or_404(komisyon_id)
    if k.odendi_mi:
        flash('Bu komisyon zaten ödenmiş.', 'info')
        return redirect(url_for('surucu_kursu.komisyon_liste'))
    if not k.komisyon_tutari or k.komisyon_tutari <= 0:
        flash('Komisyon tutarı belirtilmemiş.', 'warning')
        return redirect(url_for('surucu_kursu.komisyon_liste'))

    tarih = _date_or_none(request.form.get('odeme_tarihi')) or date.today()
    k.odendi_mi = True
    k.odeme_tarihi = tarih
    _komisyon_gider_olustur(k)
    db.session.commit()
    flash(f'Komisyon ödendi: {k.komisyon_tutari} ₺ '
          f'(muhasebe gider kaydı oluşturuldu).', 'success')
    return redirect(url_for('surucu_kursu.komisyon_liste'))


@surucu_kursu_bp.route('/komisyon/<int:komisyon_id>/odeme-iptal',
                        methods=['POST'])
@login_required
def komisyon_odeme_iptal(komisyon_id):
    """Komisyon odemesini geri al — gider kaydini sil."""
    _surucu_kursu_tenant_required()
    k = KomisyonOdemesi.query.get_or_404(komisyon_id)
    if not k.odendi_mi:
        flash('Bu komisyon zaten ödenmemiş.', 'info')
        return redirect(url_for('surucu_kursu.komisyon_liste'))
    _komisyon_gider_temizle(k)
    k.odendi_mi = False
    k.odeme_tarihi = None
    db.session.commit()
    flash('Komisyon ödemesi iptal edildi.', 'info')
    return redirect(url_for('surucu_kursu.komisyon_liste'))


@surucu_kursu_bp.route('/komisyon/<int:komisyon_id>/sil', methods=['POST'])
@login_required
def komisyon_sil(komisyon_id):
    _surucu_kursu_tenant_required()
    k = KomisyonOdemesi.query.get_or_404(komisyon_id)
    _komisyon_gider_temizle(k)
    kaynak = k.kaynak_kurs_adi
    db.session.delete(k)
    db.session.commit()
    flash(f'"{kaynak}" komisyon kaydı silindi.', 'info')
    return redirect(url_for('surucu_kursu.komisyon_liste'))
