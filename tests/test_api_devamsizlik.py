"""Mobil API — Devamsizlik endpoint testleri (Faz 3)."""
from datetime import date


def _ogrenci_kur(db_session, admin_user):
    """Ogrenci user + Ogrenci + Sinif/Sube + 3 devamsizlik kaydi."""
    from app.models.user import User
    from app.models.muhasebe import Ogrenci
    from app.models.kayit import Sinif, Sube
    from app.models.devamsizlik import Devamsizlik

    ogr_user = User(username='ogr_dev', email='ogrdev@test.local',
                    ad='Ali', soyad='Veli', rol='ogrenci', aktif=True)
    ogr_user.set_password('test12345')
    db_session.add(ogr_user)
    db_session.commit()

    ogr = Ogrenci(ogrenci_no='D100', ad='Ali', soyad='Veli',
                  tc_kimlik='11100000000', cinsiyet='erkek',
                  sinif='9-A', aktif=True, user_id=ogr_user.id)
    db_session.add(ogr)
    db_session.commit()

    sinif = Sinif(ad='9. Sınıf', seviye=9, aktif=True)
    db_session.add(sinif)
    db_session.commit()
    sube = Sube(sinif_id=sinif.id, ad='A', kontenjan=30, aktif=True)
    db_session.add(sube)
    db_session.commit()

    for ds, durum in [(1, 'devamsiz'), (2, 'devamsiz'), (3, 'gec')]:
        db_session.add(Devamsizlik(
            ogrenci_id=ogr.id, sube_id=sube.id, tarih=date(2026, 5, 4),
            ders_saati=ds, durum=durum, olusturan_id=admin_user.id,
        ))
    db_session.commit()
    return ogr_user, ogr


def _token(client, kullanici='ogr_dev', sifre='test12345'):
    r = client.post('/api/v1/auth/login', json={
        'kullanici_adi': kullanici, 'sifre': sifre,
    })
    return r.get_json()['veri']['token']


def test_ogrenci_kendi_devamsizligini_gorur(app, db_session, admin_user):
    _ogrenci_kur(db_session, admin_user)
    client = app.test_client()
    token = _token(client)
    resp = client.get('/api/v1/devamsizlik',
                       headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200
    j = resp.get_json()
    assert len(j['veri']) == 3
    assert j['ozet']['devamsiz'] == 2
    assert j['ozet']['gec'] == 1
    assert j['ozet']['toplam'] == 3
    assert j['ogrenci']['ogrenci_no'] == 'D100'


def test_ay_filtresi_calisir(app, db_session, admin_user):
    _ogrenci_kur(db_session, admin_user)
    client = app.test_client()
    token = _token(client)
    # Kayitlar 2026-05 — farkli ay bos donmeli
    resp = client.get('/api/v1/devamsizlik?ay=2026-04',
                      headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200
    assert resp.get_json()['ozet']['toplam'] == 0
    # Dogru ay
    resp2 = client.get('/api/v1/devamsizlik?ay=2026-05',
                       headers={'Authorization': f'Bearer {token}'})
    assert resp2.get_json()['ozet']['toplam'] == 3


def test_veli_cocugunun_devamsizligini_gorur(app, db_session, admin_user):
    from app.models.user import User
    from app.models.kayit import VeliBilgisi
    _, ogr = _ogrenci_kur(db_session, admin_user)

    veli_user = User(username='veli_dev', email='velidev@test.local',
                     ad='Ahmet', soyad='Veli', rol='veli', aktif=True)
    veli_user.set_password('test12345')
    db_session.add(veli_user)
    db_session.commit()
    db_session.add(VeliBilgisi(
        ogrenci_id=ogr.id, ad='Ahmet', soyad='Veli',
        yakinlik='baba', telefon='0555', user_id=veli_user.id))
    db_session.commit()

    client = app.test_client()
    token = _token(client, 'veli_dev')
    resp = client.get('/api/v1/devamsizlik',
                      headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200
    assert resp.get_json()['ozet']['toplam'] == 3


def test_ogrencisiz_hesap_404(app, db_session, admin_user):
    """Admin'in bagli ogrencisi yok -> 404."""
    client = app.test_client()
    token = _token(client, 'test_admin')
    resp = client.get('/api/v1/devamsizlik',
                      headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 404


def test_devamsizlik_tokensiz_401(app, db_session, admin_user):
    client = app.test_client()
    resp = client.get('/api/v1/devamsizlik')
    assert resp.status_code == 401
