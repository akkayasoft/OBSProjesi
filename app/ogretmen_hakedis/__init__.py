"""Ogretmen Hak Edis modulu.

Ogretmenlerin gunluk ders saatlerini Excel benzeri bir grid uzerinden
kaydeder; ay sonunda toplam saat x saatlik ucret = hak edis hesaplar.
'Odendi' isaretlenince otomatik PersonelOdemeKaydi + gider kaydi olusur.
"""
import calendar
from datetime import date
from decimal import Decimal, InvalidOperation

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, abort)
from flask_login import login_required, current_user
from sqlalchemy import extract, func

from app.extensions import db
from app.utils import role_required
from app.models.muhasebe import (Personel, PersonelOdemeKaydi, BankaHesabi,
                                 OgretmenDersSaati)
from app.muhasebe.utils import (personel_odemesi_icin_gider_kaydi_olustur,
                                banka_hareketi_olustur)

ogretmen_hakedis_bp = Blueprint(
    'ogretmen_hakedis', __name__,
    template_folder='../templates/ogretmen_hakedis',
)

HAKEDIS_ISARET = 'ders saati hak edişi'


# -------------------------------------------------------------------
# Yardimcilar
# -------------------------------------------------------------------
def _gecerli_ay(ay_str):
    """'2026-01' -> (2026, 1). Gecersizse bu ay."""
    bugun = date.today()
    if ay_str:
        try:
            yil, ay = ay_str.split('-')
            yil, ay = int(yil), int(ay)
            if 1 <= ay <= 12 and 2000 <= yil <= 2100:
                return yil, ay
        except (ValueError, AttributeError):
            pass
    return bugun.year, bugun.month


def _ay_str(yil, ay):
    return f'{yil:04d}-{ay:02d}'


def _ay_etiket(yil, ay):
    aylar = ['', 'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
             'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
    return f'{aylar[ay]} {yil}'


def _komsu_aylar(yil, ay):
    onceki = (yil - 1, 12) if ay == 1 else (yil, ay - 1)
    sonraki = (yil + 1, 1) if ay == 12 else (yil, ay + 1)
    return _ay_str(*onceki), _ay_str(*sonraki)


def _personeller():
    """Aktif personeller — departman (brans) sonra ad sirali."""
    return Personel.query.filter_by(aktif=True).order_by(
        Personel.departman.asc(),
        Personel.ad.asc(),
    ).all()


def _ay_saatleri(yil, ay):
    """O ay icindeki tum OgretmenDersSaati kayitlari ->
    {(personel_id, gun): saat}."""
    kayitlar = OgretmenDersSaati.query.filter(
        extract('year', OgretmenDersSaati.tarih) == yil,
        extract('month', OgretmenDersSaati.tarih) == ay,
    ).all()
    return {(k.personel_id, k.tarih.day): k for k in kayitlar}


def _personel_ay_toplami(personel_id, yil, ay):
    """Bir personelin o ayki toplam ders saati."""
    toplam = db.session.query(
        func.coalesce(func.sum(OgretmenDersSaati.saat), 0)
    ).filter(
        OgretmenDersSaati.personel_id == personel_id,
        extract('year', OgretmenDersSaati.tarih) == yil,
        extract('month', OgretmenDersSaati.tarih) == ay,
    ).scalar()
    return Decimal(str(toplam or 0))


def _hakedis_odemesi(personel_id, donem):
    """O personel+donem icin hak edis odeme kaydi (varsa)."""
    return PersonelOdemeKaydi.query.filter(
        PersonelOdemeKaydi.personel_id == personel_id,
        PersonelOdemeKaydi.donem == donem,
        PersonelOdemeKaydi.aciklama.ilike(f'%{HAKEDIS_ISARET}%'),
    ).first()


# -------------------------------------------------------------------
# Rotalar
# -------------------------------------------------------------------
@ogretmen_hakedis_bp.route('/')
@login_required
@role_required('admin', 'yonetici', 'muhasebeci')
def index():
    return redirect(url_for('ogretmen_hakedis.maliyet'))


@ogretmen_hakedis_bp.route('/giris', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'yonetici', 'muhasebeci')
def giris():
    yil, ay = _gecerli_ay(request.values.get('ay'))
    donem = _ay_str(yil, ay)
    gun_sayisi = calendar.monthrange(yil, ay)[1]
    personeller = _personeller()

    if request.method == 'POST':
        mevcut = _ay_saatleri(yil, ay)
        degisen = 0
        for p in personeller:
            for gun in range(1, gun_sayisi + 1):
                alan = request.form.get(f's_{p.id}_{gun}', '').strip()
                anahtar = (p.id, gun)
                kayit = mevcut.get(anahtar)
                if alan == '':
                    # Bos -> varsa kaydi sil
                    if kayit is not None:
                        db.session.delete(kayit)
                        degisen += 1
                    continue
                try:
                    saat = Decimal(alan.replace(',', '.'))
                except (InvalidOperation, ValueError):
                    continue
                if saat < 0:
                    continue
                if kayit is None:
                    db.session.add(OgretmenDersSaati(
                        personel_id=p.id,
                        tarih=date(yil, ay, gun),
                        saat=saat,
                        olusturan_id=current_user.id,
                    ))
                    degisen += 1
                elif Decimal(str(kayit.saat)) != saat:
                    kayit.saat = saat
                    degisen += 1
        db.session.commit()
        flash(f'{_ay_etiket(yil, ay)} ders saatleri kaydedildi '
              f'({degisen} değişiklik).', 'success')
        return redirect(url_for('ogretmen_hakedis.giris', ay=donem))

    saatler = _ay_saatleri(yil, ay)
    # Grid satirlari: her personel icin gun -> saat
    satirlar = []
    for p in personeller:
        gunler = {}
        toplam = Decimal('0')
        for gun in range(1, gun_sayisi + 1):
            k = saatler.get((p.id, gun))
            if k is not None:
                gunler[gun] = k.saat
                toplam += Decimal(str(k.saat))
        satirlar.append({'personel': p, 'gunler': gunler, 'toplam': toplam})

    onceki_ay, sonraki_ay = _komsu_aylar(yil, ay)
    return render_template(
        'ogretmen_hakedis/giris.html',
        satirlar=satirlar, gun_sayisi=gun_sayisi,
        gunler=list(range(1, gun_sayisi + 1)),
        donem=donem, ay_etiket=_ay_etiket(yil, ay),
        onceki_ay=onceki_ay, sonraki_ay=sonraki_ay,
    )


@ogretmen_hakedis_bp.route('/maliyet')
@login_required
@role_required('admin', 'yonetici', 'muhasebeci')
def maliyet():
    yil, ay = _gecerli_ay(request.values.get('ay'))
    donem = _ay_str(yil, ay)
    personeller = _personeller()

    # Brans (departman) bazli gruplama
    gruplar = {}
    genel_saat = Decimal('0')
    genel_tutar = Decimal('0')
    for p in personeller:
        toplam_saat = _personel_ay_toplami(p.id, yil, ay)
        ucret = Decimal(str(p.saatlik_ucret or 0))
        tutar = toplam_saat * ucret
        odeme = _hakedis_odemesi(p.id, donem)
        # Saati ve ucreti olmayan personeli atla (gurultu olmasin)
        if toplam_saat == 0 and ucret == 0 and odeme is None:
            continue
        brans = p.departman or 'Diğer'
        gruplar.setdefault(brans, [])
        gruplar[brans].append({
            'personel': p,
            'toplam_saat': toplam_saat,
            'saatlik_ucret': ucret,
            'tutar': tutar,
            'odeme': odeme,
        })
        genel_saat += toplam_saat
        genel_tutar += tutar

    # Grup alt toplamlari
    grup_listesi = []
    for brans in sorted(gruplar.keys()):
        satirlar = gruplar[brans]
        grup_listesi.append({
            'brans': brans,
            'satirlar': satirlar,
            'alt_saat': sum((s['toplam_saat'] for s in satirlar), Decimal('0')),
            'alt_tutar': sum((s['tutar'] for s in satirlar), Decimal('0')),
        })

    hesaplar = BankaHesabi.query.filter_by(aktif=True).all()
    onceki_ay, sonraki_ay = _komsu_aylar(yil, ay)
    return render_template(
        'ogretmen_hakedis/maliyet.html',
        grup_listesi=grup_listesi,
        genel_saat=genel_saat, genel_tutar=genel_tutar,
        donem=donem, ay_etiket=_ay_etiket(yil, ay),
        onceki_ay=onceki_ay, sonraki_ay=sonraki_ay,
        hesaplar=hesaplar,
    )


@ogretmen_hakedis_bp.route('/saatlik-ucret/<int:personel_id>', methods=['POST'])
@login_required
@role_required('admin', 'yonetici', 'muhasebeci')
def saatlik_ucret(personel_id):
    personel = Personel.query.get_or_404(personel_id)
    donem = request.form.get('ay') or ''
    deger = (request.form.get('saatlik_ucret') or '').strip().replace(',', '.')
    try:
        ucret = Decimal(deger)
        if ucret < 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        flash('Geçersiz saatlik ücret.', 'danger')
        return redirect(url_for('ogretmen_hakedis.maliyet', ay=donem))
    personel.saatlik_ucret = ucret
    db.session.commit()
    flash(f'{personel.tam_ad} saatlik ücreti {ucret} ₺ olarak güncellendi.',
          'success')
    return redirect(url_for('ogretmen_hakedis.maliyet', ay=donem))


@ogretmen_hakedis_bp.route('/ode/<int:personel_id>', methods=['POST'])
@login_required
@role_required('admin', 'yonetici', 'muhasebeci')
def ode(personel_id):
    personel = Personel.query.get_or_404(personel_id)
    donem = request.form.get('ay') or ''
    yil, ay = _gecerli_ay(donem)
    donem = _ay_str(yil, ay)

    if _hakedis_odemesi(personel_id, donem) is not None:
        flash(f'{personel.tam_ad} için {_ay_etiket(yil, ay)} hak edişi '
              f'zaten ödenmiş.', 'info')
        return redirect(url_for('ogretmen_hakedis.maliyet', ay=donem))

    toplam_saat = _personel_ay_toplami(personel_id, yil, ay)
    ucret = Decimal(str(personel.saatlik_ucret or 0))
    tutar = toplam_saat * ucret
    if tutar <= 0:
        flash('Ödenecek tutar sıfır. Önce ders saati ve saatlik ücret '
              'tanımlayın.', 'danger')
        return redirect(url_for('ogretmen_hakedis.maliyet', ay=donem))

    odeme_turu = request.form.get('odeme_turu') or 'havale'
    banka_hesap_id = request.form.get('banka_hesap_id')
    banka_hesap_id = int(banka_hesap_id) if banka_hesap_id and \
        banka_hesap_id.isdigit() and int(banka_hesap_id) > 0 else None

    aciklama = (f'{personel.tam_ad} — {_ay_etiket(yil, ay)} {HAKEDIS_ISARET} '
                f'({toplam_saat} saat × {ucret} ₺)')
    odeme = PersonelOdemeKaydi(
        personel_id=personel_id,
        donem=donem,
        tutar=tutar,
        odeme_turu=odeme_turu,
        banka_hesap_id=banka_hesap_id,
        aciklama=aciklama,
        tarih=date.today(),
        olusturan_id=current_user.id,
    )
    db.session.add(odeme)
    db.session.flush()

    if banka_hesap_id:
        banka_hareketi_olustur(
            banka_hesap_id, 'cikis', tutar,
            aciklama=f'Öğretmen hak edişi: {personel.tam_ad} ({donem})',
        )
    # Otomatik 'Personel Maaslari' gider kaydi
    personel_odemesi_icin_gider_kaydi_olustur(odeme)
    db.session.commit()

    flash(f'{personel.tam_ad} — {_ay_etiket(yil, ay)} hak edişi '
          f'{tutar:.2f} ₺ ödendi olarak kaydedildi.', 'success')
    return redirect(url_for('ogretmen_hakedis.maliyet', ay=donem))


@ogretmen_hakedis_bp.route('/ode-geri-al/<int:odeme_id>', methods=['POST'])
@login_required
@role_required('admin', 'yonetici', 'muhasebeci')
def ode_geri_al(odeme_id):
    """Hak edis odemesini geri al (yanlislikla isaretlenmis ise)."""
    from app.muhasebe.utils import personel_odeme_gider_kaydini_temizle
    odeme = PersonelOdemeKaydi.query.get_or_404(odeme_id)
    donem = odeme.donem
    if HAKEDIS_ISARET not in (odeme.aciklama or ''):
        abort(404)
    personel_odeme_gider_kaydini_temizle(odeme)
    db.session.delete(odeme)
    db.session.commit()
    flash('Hak edişi ödemesi geri alındı.', 'success')
    return redirect(url_for('ogretmen_hakedis.maliyet', ay=donem))
