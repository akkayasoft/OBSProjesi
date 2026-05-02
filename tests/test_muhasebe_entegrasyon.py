"""Muhasebe modulu entegrasyon regresyon testleri.

Bu testler 'X islemi yapildiginda Y'de de gorulmeli mi?' sorularini
otomatik dogrular. Tarihte bulunan bug'lar:
  - 2026-04-30: Ogrenci odemesi alindiginda Gelir/Gider'e yansimiyordu
  - 2026-05-02: Personel maas odemesi ayni bug
  - 2026-05-02: Kantin satisi ayni bug

Eger biri tekrar regresyon olursa bu testler PASS'tan FAIL'e doner.
"""
from datetime import date
from decimal import Decimal


def _yeni_kategori(db_session, ad, tur):
    """Test kategorisi olustur (idempotent)."""
    from app.models.muhasebe import GelirGiderKategorisi
    k = GelirGiderKategorisi.query.filter_by(ad=ad, tur=tur).first()
    if k is None:
        k = GelirGiderKategorisi(ad=ad, tur=tur, aktif=True)
        db_session.add(k)
        db_session.commit()
    return k


# ============================================================
# Test 1: Ogrenci taksit odemesi -> Gelir/Gider'e yansimali
# ============================================================
def test_ogrenci_odemesi_otomatik_gelir_kaydi_olusturur(
    app, db_session, ogrenci_with_plan, banka_hesap, admin_user,
):
    """Bug: Faz 3 oncesi bu yansima yoktu — odeme alinirdi ama
    Gelir/Gider raporunda gorunmezdi."""
    from app.models.muhasebe import Odeme, Taksit, GelirGiderKaydi
    from app.muhasebe.utils import (
        odeme_icin_gelir_kaydi_olustur, makbuz_no_uret,
    )

    _, plan = ogrenci_with_plan
    taksit = Taksit.query.filter_by(odeme_plani_id=plan.id, taksit_no=1).first()

    odeme = Odeme(
        taksit_id=taksit.id, tutar=Decimal('3000'),
        odeme_turu='nakit', banka_hesap_id=banka_hesap.id,
        makbuz_no=makbuz_no_uret(),
        olusturan_id=admin_user.id,
    )
    db_session.add(odeme)
    db_session.flush()

    # Helper'i cagir (route'da odeme_yap yapiyor)
    odeme_icin_gelir_kaydi_olustur(odeme)
    db_session.commit()

    # Doğrulama: Odeme'ye linkli bir GelirGiderKaydi olusmali
    assert odeme.gelir_gider_kayit_id is not None, \
        'Odeme alindi ama Gelir/Gider kaydi olusturulmadi!'

    kayit = GelirGiderKaydi.query.get(odeme.gelir_gider_kayit_id)
    assert kayit is not None
    assert kayit.tur == 'gelir'
    assert kayit.tutar == Decimal('3000')
    assert kayit.belge_no == odeme.makbuz_no
    assert 'Aidatı' in kayit.kategori.ad or 'Aidat' in kayit.kategori.ad


def test_ogrenci_odemesi_iptal_gelir_kaydini_siler(
    app, db_session, ogrenci_with_plan, banka_hesap, admin_user,
):
    """Iptal edildiginde linkli gelir kaydi temizlenir."""
    from app.models.muhasebe import Odeme, Taksit, GelirGiderKaydi
    from app.muhasebe.utils import (
        odeme_icin_gelir_kaydi_olustur, odeme_gelir_kaydini_temizle,
        makbuz_no_uret,
    )

    _, plan = ogrenci_with_plan
    taksit = Taksit.query.filter_by(odeme_plani_id=plan.id, taksit_no=1).first()
    odeme = Odeme(
        taksit_id=taksit.id, tutar=Decimal('3000'),
        odeme_turu='nakit', banka_hesap_id=banka_hesap.id,
        makbuz_no=makbuz_no_uret(),
        olusturan_id=admin_user.id,
    )
    db_session.add(odeme)
    db_session.flush()
    odeme_icin_gelir_kaydi_olustur(odeme)
    db_session.commit()

    kayit_id = odeme.gelir_gider_kayit_id
    assert kayit_id is not None

    # Iptal et
    odeme_gelir_kaydini_temizle(odeme)
    db_session.commit()

    assert odeme.gelir_gider_kayit_id is None
    assert GelirGiderKaydi.query.get(kayit_id) is None, \
        'Iptal sonrasi gelir kaydi hala duruyor!'


# ============================================================
# Test 2: Personel maas odemesi -> Gider'e yansimali
# ============================================================
def test_personel_odemesi_otomatik_gider_kaydi_olusturur(
    app, db_session, banka_hesap, admin_user,
):
    """Bulgu A: Personel maas odemesi yıllarca Gider raporuna yansimazdi."""
    from app.models.muhasebe import Personel, PersonelOdemeKaydi, GelirGiderKaydi
    from app.muhasebe.utils import personel_odemesi_icin_gider_kaydi_olustur

    p = Personel(
        sicil_no='P001', ad='Mehmet', soyad='Test',
        pozisyon='Ogretmen', maas=Decimal('25000'),
        aktif=True,
    )
    db_session.add(p)
    db_session.commit()

    odeme = PersonelOdemeKaydi(
        personel_id=p.id, donem='2026-04',
        tutar=Decimal('25000'), odeme_turu='banka',
        banka_hesap_id=banka_hesap.id,
        olusturan_id=admin_user.id,
        tarih=date.today(),
    )
    db_session.add(odeme)
    db_session.flush()
    personel_odemesi_icin_gider_kaydi_olustur(odeme)
    db_session.commit()

    assert odeme.gelir_gider_kayit_id is not None, \
        'Personel odemesi yapildi ama Gider kaydi olusturulmadi!'
    kayit = GelirGiderKaydi.query.get(odeme.gelir_gider_kayit_id)
    assert kayit.tur == 'gider'
    assert kayit.tutar == Decimal('25000')
    assert kayit.kategori.ad == 'Personel Maaşları'


# ============================================================
# Test 3: Kantin satisi -> Gelir'e yansimali
# ============================================================
def test_kantin_satisi_otomatik_gelir_kaydi_olusturur(
    app, db_session, admin_user,
):
    """Bulgu B: Kantin satisi Gelir'e yansimiyordu."""
    from app.models.kantin import KantinUrun, KantinSatis
    from app.models.muhasebe import GelirGiderKaydi
    from app.muhasebe.utils import kantin_satisi_icin_gelir_kaydi_olustur

    urun = KantinUrun(ad='Su', kategori='icecek', fiyat=10.0,
                      stok=100, aktif=True)
    db_session.add(urun)
    db_session.commit()

    satis = KantinSatis(
        urun_id=urun.id, miktar=3, toplam_fiyat=30.0,
    )
    db_session.add(satis)
    db_session.flush()
    kantin_satisi_icin_gelir_kaydi_olustur(satis, admin_user.id)
    db_session.commit()

    assert satis.gelir_gider_kayit_id is not None, \
        'Kantin satisi yapildi ama Gelir kaydi olusturulmadi!'
    kayit = GelirGiderKaydi.query.get(satis.gelir_gider_kayit_id)
    assert kayit.tur == 'gelir'
    assert float(kayit.tutar) == 30.0
    assert kayit.kategori.ad == 'Kantin Geliri'


# ============================================================
# Test 4: Idempotency — ayni odeme icin 2 kez cagrilirsa duplicate yok
# ============================================================
def test_otomatik_gelir_kaydi_idempotent(
    app, db_session, ogrenci_with_plan, banka_hesap, admin_user,
):
    from app.models.muhasebe import Odeme, Taksit, GelirGiderKaydi
    from app.muhasebe.utils import (
        odeme_icin_gelir_kaydi_olustur, makbuz_no_uret,
    )

    _, plan = ogrenci_with_plan
    taksit = Taksit.query.filter_by(odeme_plani_id=plan.id, taksit_no=1).first()
    odeme = Odeme(
        taksit_id=taksit.id, tutar=Decimal('3000'),
        odeme_turu='nakit', banka_hesap_id=banka_hesap.id,
        makbuz_no=makbuz_no_uret(),
        olusturan_id=admin_user.id,
    )
    db_session.add(odeme)
    db_session.flush()

    # 2 kere cagir — sadece 1 gelir kaydi olusmalı
    odeme_icin_gelir_kaydi_olustur(odeme)
    odeme_icin_gelir_kaydi_olustur(odeme)
    db_session.commit()

    aidat_kayitlari = GelirGiderKaydi.query.filter_by(
        belge_no=odeme.makbuz_no,
    ).all()
    assert len(aidat_kayitlari) == 1, \
        f'Idempotency bozuk: {len(aidat_kayitlari)} kayit olustu'
