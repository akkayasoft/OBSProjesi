"""Surucu kursu modulu testleri.

Sinav harci tahsil edildiginde muhasebede otomatik gelir kaydi
olusturur (Faz 2.D). Tahsilat geri alinirsa kayit silinir.
"""
from datetime import date
from decimal import Decimal


def _surucu_test_kursiyer(db_session):
    """Test kursiyeri olustur."""
    from app.models.surucu_kursu import Kursiyer
    k = Kursiyer(
        ad='Ayse', soyad='Test', telefon='0555 000 00 00',
        kayit_tarihi=date.today(),
        ehliyet_sinifi='B_otomatik',
        ders_sayisi=28,
        fiyat=Decimal('11000'),
        aktif=True,
    )
    db_session.add(k)
    db_session.commit()
    return k


def test_sinav_harci_tahsil_edildiginde_gelir_kaydi_olusur(
    app, db_session, admin_user,
):
    """Bug regresyonu: tahsilat butonu basildiktan sonra Gelir/Gider'de
    otomatik kayit olusmali."""
    from app.models.surucu_kursu import (
        SurucuSinavOturumu, SurucuSinavHarciKaydi,
    )
    from app.models.muhasebe import GelirGiderKaydi

    # Flask-Login current_user'i simule et — helper current_user.id istiyor
    with app.test_request_context():
        from flask_login import login_user
        login_user(admin_user)

        kursiyer = _surucu_test_kursiyer(db_session)
        oturum = SurucuSinavOturumu(
            sinav_tarihi=date(2026, 5, 15),
            sinav_tipi='yazili', notlar='Test oturumu',
        )
        db_session.add(oturum)
        db_session.commit()

        harc = SurucuSinavHarciKaydi(
            sinav_oturum_id=oturum.id,
            kursiyer_id=kursiyer.id,
            ucret=Decimal('750'),
            durum='aday_borclu',
        )
        db_session.add(harc)
        db_session.commit()

        # Tahsil et — otomatik gelir kaydi olusmali
        from app.surucu_kursu.routes import _muhasebe_kaydi_olustur
        harc.durum = 'tahsil_edildi'
        harc.tahsil_tarihi = date.today()
        _muhasebe_kaydi_olustur(harc)
        db_session.commit()

        assert harc.gelir_gider_kayit_id is not None, \
            'Sinav harci tahsil edildi ama gelir kaydi olusturulmadi!'

        kayit = GelirGiderKaydi.query.get(harc.gelir_gider_kayit_id)
        assert kayit is not None
        assert kayit.tur == 'gelir'
        assert kayit.tutar == Decimal('750')
        assert kayit.kategori.ad == 'Sınav Harç Tahsilatı'
        assert kayit.belge_no == f'SHARC-{harc.id}'


def test_kursiyer_taksiti_odendiginde_gelir_kaydi_olusur(
    app, db_session, admin_user,
):
    """Bug regresyonu: kursiyer egitim ucreti taksiti odendi
    isaretlendiginde Surucu Kursu Geliri kategorisinde otomatik kayit
    olusmali."""
    from app.models.surucu_kursu import KursiyerTaksit
    from app.models.muhasebe import GelirGiderKaydi
    from datetime import date as _d
    from decimal import Decimal as _D

    with app.test_request_context():
        from flask_login import login_user
        login_user(admin_user)

        kursiyer = _surucu_test_kursiyer(db_session)
        t = KursiyerTaksit(
            kursiyer_id=kursiyer.id, sira=1,
            vade_tarihi=_d(2026, 6, 1), tutar=_D('3000'),
            odendi_mi=False,
        )
        db_session.add(t)
        db_session.commit()

        # Toggle: odendi yap
        from app.surucu_kursu.routes import (
            _kursiyer_taksit_gelir_kaydi_olustur,
        )
        t.odendi_mi = True
        t.odeme_tarihi = _d.today()
        _kursiyer_taksit_gelir_kaydi_olustur(t)
        db_session.commit()

        assert t.gelir_gider_kayit_id is not None, \
            'Kursiyer taksiti odendi ama gelir kaydi olusturulmadi!'
        kayit = GelirGiderKaydi.query.get(t.gelir_gider_kayit_id)
        assert kayit.tur == 'gelir'
        assert kayit.tutar == _D('3000')
        assert kayit.kategori.ad == 'Sürücü Kursu Geliri'
        assert kayit.belge_no == f'KT-{t.id}'


def test_kursiyer_taksiti_geri_alindiginda_gelir_silinir(
    app, db_session, admin_user,
):
    """Toggle off — bagli kayit temizlenmeli."""
    from app.models.surucu_kursu import KursiyerTaksit
    from app.models.muhasebe import GelirGiderKaydi
    from datetime import date as _d
    from decimal import Decimal as _D

    with app.test_request_context():
        from flask_login import login_user
        login_user(admin_user)

        kursiyer = _surucu_test_kursiyer(db_session)
        t = KursiyerTaksit(
            kursiyer_id=kursiyer.id, sira=1,
            vade_tarihi=_d(2026, 6, 1), tutar=_D('3000'),
            odendi_mi=True, odeme_tarihi=_d.today(),
        )
        db_session.add(t)
        db_session.commit()

        from app.surucu_kursu.routes import (
            _kursiyer_taksit_gelir_kaydi_olustur,
            _kursiyer_taksit_gelir_kaydi_temizle,
        )
        _kursiyer_taksit_gelir_kaydi_olustur(t)
        db_session.commit()
        kayit_id = t.gelir_gider_kayit_id
        assert kayit_id is not None

        # Geri al
        _kursiyer_taksit_gelir_kaydi_temizle(t)
        t.odendi_mi = False
        t.odeme_tarihi = None
        db_session.commit()

        assert t.gelir_gider_kayit_id is None
        assert GelirGiderKaydi.query.get(kayit_id) is None


def test_sinav_harci_tahsil_geri_alindiginda_gelir_silinir(
    app, db_session, admin_user,
):
    """Geri al butonu — bagli muhasebe kaydi temizlenmeli."""
    from app.models.surucu_kursu import (
        SurucuSinavOturumu, SurucuSinavHarciKaydi,
    )
    from app.models.muhasebe import GelirGiderKaydi

    with app.test_request_context():
        from flask_login import login_user
        login_user(admin_user)

        kursiyer = _surucu_test_kursiyer(db_session)
        oturum = SurucuSinavOturumu(
            sinav_tarihi=date(2026, 5, 15), sinav_tipi='direksiyon',
        )
        db_session.add(oturum)
        db_session.commit()

        harc = SurucuSinavHarciKaydi(
            sinav_oturum_id=oturum.id, kursiyer_id=kursiyer.id,
            ucret=Decimal('1200'), durum='aday_borclu',
        )
        db_session.add(harc)
        db_session.commit()

        # Tahsil et
        from app.surucu_kursu.routes import (
            _muhasebe_kaydi_olustur, _muhasebe_kaydi_temizle,
        )
        harc.durum = 'tahsil_edildi'
        harc.tahsil_tarihi = date.today()
        _muhasebe_kaydi_olustur(harc)
        db_session.commit()
        kayit_id = harc.gelir_gider_kayit_id

        # Geri al
        _muhasebe_kaydi_temizle(harc)
        harc.durum = 'aday_borclu'
        harc.tahsil_tarihi = None
        db_session.commit()

        assert harc.gelir_gider_kayit_id is None
        assert GelirGiderKaydi.query.get(kayit_id) is None
