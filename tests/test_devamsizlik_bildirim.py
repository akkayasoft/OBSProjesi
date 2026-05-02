"""Devamsizlik bildirim regresyon testleri.

Bulgu D: Yoklama 'devamsiz' isaretlenince ogrenciye + velilerine
otomatik Bildirim olusmali.
"""
from datetime import date


def _devamsiz_setup(db_session, admin_user):
    """Test ogrenci + veli (her ikisi de portal user'a sahip) + sube."""
    from app.models.user import User
    from app.models.muhasebe import Ogrenci
    from app.models.kayit import VeliBilgisi, Sube, Sinif

    ogr_user = User(username='ogr_test', email='ogr@test.local',
                    ad='Ali', soyad='Ogr', rol='ogrenci', aktif=True)
    ogr_user.set_password('test')
    veli_user = User(username='veli_test', email='veli@test.local',
                     ad='Ahmet', soyad='Ogr', rol='veli', aktif=True)
    veli_user.set_password('test')
    db_session.add_all([ogr_user, veli_user])
    db_session.commit()

    ogr = Ogrenci(
        ogrenci_no='T002', ad='Ali', soyad='Ogr',
        tc_kimlik='10000000001', cinsiyet='Erkek',
        sinif='9-A', aktif=True, user_id=ogr_user.id,
    )
    db_session.add(ogr)
    db_session.commit()

    veli = VeliBilgisi(
        ogrenci_id=ogr.id, ad='Ahmet', soyad='Ogr',
        yakinlik='baba', telefon='0555 555 55 55',
        user_id=veli_user.id,
    )
    db_session.add(veli)

    sinif = Sinif(ad='9. Sınıf', seviye=9, aktif=True)
    db_session.add(sinif)
    db_session.commit()
    sube = Sube(sinif_id=sinif.id, ad='A', kontenjan=30, aktif=True)
    db_session.add(sube)
    db_session.commit()

    return ogr, ogr_user, veli_user, sube


def test_devamsiz_isaretlendiginde_ogrenciye_ve_veliye_bildirim_atilir(
    app, db_session, admin_user,
):
    from app.models.devamsizlik import Devamsizlik
    from app.models.bildirim import Bildirim
    from app.devamsizlik.bildirim import devamsizlik_bildirimleri_gonder

    ogr, ogr_user, veli_user, sube = _devamsiz_setup(db_session, admin_user)

    d = Devamsizlik(
        ogrenci_id=ogr.id, sube_id=sube.id,
        tarih=date.today(), ders_saati=2,
        durum='devamsiz', olusturan_id=admin_user.id,
    )
    db_session.add(d)
    db_session.flush()

    sayi = devamsizlik_bildirimleri_gonder([d])
    db_session.commit()

    assert sayi == 2, f'2 bildirim beklendi (ogrenci+veli), {sayi} olustu'

    # Hem ogrencinin hem velinin bildirim'i olmali
    ogr_bildirim = Bildirim.query.filter_by(kullanici_id=ogr_user.id).first()
    veli_bildirim = Bildirim.query.filter_by(kullanici_id=veli_user.id).first()

    assert ogr_bildirim is not None
    assert veli_bildirim is not None
    assert ogr_bildirim.kategori == 'devamsizlik'
    assert ogr_bildirim.tur == 'uyari'
    assert veli_bildirim.kategori == 'devamsizlik'


def test_birden_fazla_ders_saati_tek_bildirim_konsolide(
    app, db_session, admin_user,
):
    """Ayni gun 3 ders saati devamsiz ise tek bildirim olustu (spam azalt)."""
    from app.models.devamsizlik import Devamsizlik
    from app.models.bildirim import Bildirim
    from app.devamsizlik.bildirim import devamsizlik_bildirimleri_gonder

    ogr, ogr_user, veli_user, sube = _devamsiz_setup(db_session, admin_user)

    kayitlar = []
    for ds in (1, 2, 3):
        d = Devamsizlik(
            ogrenci_id=ogr.id, sube_id=sube.id,
            tarih=date.today(), ders_saati=ds,
            durum='devamsiz', olusturan_id=admin_user.id,
        )
        db_session.add(d)
        kayitlar.append(d)
    db_session.flush()

    sayi = devamsizlik_bildirimleri_gonder(kayitlar)
    db_session.commit()

    # 3 ders saati ama 2 bildirim (1 ogrenciye, 1 veliye) — konsolide
    assert sayi == 2, f'Konsolidasyon bozuk: {sayi} bildirim olustu (2 olmaliydi)'

    veli_bildirim = Bildirim.query.filter_by(kullanici_id=veli_user.id).first()
    # Mesaj icinde "3 ders saati" gecmeli
    assert '3 ders saati' in veli_bildirim.mesaj or '(1, 2, 3' in veli_bildirim.mesaj


def test_gec_izinli_raporlu_durumlarda_bildirim_atilmaz(
    app, db_session, admin_user,
):
    """Sadece 'devamsiz' icin bildirim — gec/izinli/raporlu aklin."""
    from app.models.devamsizlik import Devamsizlik
    from app.devamsizlik.bildirim import devamsizlik_bildirimleri_gonder

    ogr, *_ = _devamsiz_setup(db_session, admin_user)

    kayitlar = []
    for durum in ('gec', 'izinli', 'raporlu'):
        d = Devamsizlik(
            ogrenci_id=ogr.id, sube_id=1,
            tarih=date.today(), ders_saati=1,
            durum=durum, olusturan_id=admin_user.id,
        )
        kayitlar.append(d)

    sayi = devamsizlik_bildirimleri_gonder(kayitlar)
    assert sayi == 0


def test_bildirim_ayari_kapaliysa_atlanır(
    app, db_session, admin_user,
):
    """SistemAyar.otomatik_bildirim=false ise bildirim atilmaz."""
    from app.models.ayarlar import SistemAyar
    from app.models.devamsizlik import Devamsizlik
    from app.devamsizlik.bildirim import devamsizlik_bildirimleri_gonder

    db_session.add(SistemAyar(
        anahtar='otomatik_bildirim', deger='false',
        aciklama='Test', kategori='iletisim', tur='boolean',
        varsayilan='true',
    ))
    db_session.commit()

    ogr, *_ = _devamsiz_setup(db_session, admin_user)
    d = Devamsizlik(
        ogrenci_id=ogr.id, sube_id=1,
        tarih=date.today(), ders_saati=1,
        durum='devamsiz', olusturan_id=admin_user.id,
    )

    sayi = devamsizlik_bildirimleri_gonder([d])
    assert sayi == 0, 'Ayar kapali ama bildirim atildi!'
