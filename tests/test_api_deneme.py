"""Mobil API — Deneme sinavi endpoint testleri (Faz 5)."""
from datetime import date


def _kur(db_session, admin_user):
    """Ogrenci user + Ogrenci + DenemeSinavi + 2 ders + katilim + sonuc."""
    from app.models.user import User
    from app.models.muhasebe import Ogrenci
    from app.models.deneme_sinavi import (
        DenemeSinavi, DenemeDersi, DenemeKatilim, DenemeDersSonucu)

    u = User(username='ogr_den', email='ogrden@test.local',
             ad='Zeynep', soyad='Net', rol='ogrenci', aktif=True)
    u.set_password('test12345')
    db_session.add(u)
    db_session.commit()

    ogr = Ogrenci(ogrenci_no='N300', ad='Zeynep', soyad='Net',
                  tc_kimlik='33300000000', cinsiyet='kiz',
                  sinif='12-A', aktif=True, user_id=u.id)
    db_session.add(ogr)
    db_session.commit()

    sinav = DenemeSinavi(ad='TYT Deneme 1', sinav_tipi='tyt',
                         donem='2025-2026', tarih=date(2026, 5, 1),
                         durum='tamamlandi', olusturan_id=admin_user.id)
    db_session.add(sinav)
    db_session.commit()

    d1 = DenemeDersi(deneme_sinavi_id=sinav.id, ders_kodu='turkce',
                     ders_adi='Türkçe', soru_sayisi=40, sira=1)
    d2 = DenemeDersi(deneme_sinavi_id=sinav.id, ders_kodu='matematik',
                     ders_adi='Matematik', soru_sayisi=40, sira=2)
    db_session.add_all([d1, d2])
    db_session.commit()

    # Ogrencimizin katilimi: net 30
    k = DenemeKatilim(deneme_sinavi_id=sinav.id, ogrenci_id=ogr.id,
                      katildi=True, toplam_dogru=35, toplam_yanlis=20,
                      toplam_bos=25, toplam_net=30.0, toplam_puan=300.0)
    db_session.add(k)
    db_session.commit()
    db_session.add(DenemeDersSonucu(katilim_id=k.id, deneme_dersi_id=d1.id,
                                    dogru=20, yanlis=8, bos=12, net=18.0))
    db_session.add(DenemeDersSonucu(katilim_id=k.id, deneme_dersi_id=d2.id,
                                    dogru=15, yanlis=12, bos=13, net=12.0))
    db_session.commit()

    # Daha yuksek netli baska bir katilimci (siralama testi icin)
    ogr2 = Ogrenci(ogrenci_no='N301', ad='Diger', soyad='Ogr',
                   tc_kimlik='33300000001', cinsiyet='erkek',
                   sinif='12-A', aktif=True)
    db_session.add(ogr2)
    db_session.commit()
    db_session.add(DenemeKatilim(
        deneme_sinavi_id=sinav.id, ogrenci_id=ogr2.id, katildi=True,
        toplam_net=50.0, toplam_puan=400.0))
    db_session.commit()
    return u, ogr, k


def _token(client, kullanici, sifre='test12345'):
    r = client.post('/api/v1/auth/login', json={
        'kullanici_adi': kullanici, 'sifre': sifre})
    return r.get_json()['veri']['token']


def test_deneme_listesi(app, db_session, admin_user):
    _kur(db_session, admin_user)
    client = app.test_client()
    token = _token(client, 'ogr_den')
    resp = client.get('/api/v1/denemeler',
                       headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200
    veri = resp.get_json()['veri']
    assert len(veri) == 1
    assert veri[0]['toplam_net'] == 30.0
    assert veri[0]['sinav']['ad'] == 'TYT Deneme 1'


def test_deneme_detay_ders_sonuclari_ve_siralama(app, db_session, admin_user):
    _, _, k = _kur(db_session, admin_user)
    client = app.test_client()
    token = _token(client, 'ogr_den')
    resp = client.get(f'/api/v1/denemeler/{k.id}',
                       headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200
    veri = resp.get_json()['veri']
    assert len(veri['ders_sonuclari']) == 2
    # Net 30 — net 50'li bir kisi var, dolayisiyla 2. sirada
    assert veri['siralama'] == 2
    assert veri['toplam_katilimci'] == 2
    assert veri['sonuc']['toplam_net'] == 30.0


def test_baskasinin_deneme_detayi_404(app, db_session, admin_user):
    """Ogrenci baska ogrencinin katilimina erisemez."""
    from app.models.deneme_sinavi import DenemeKatilim
    _kur(db_session, admin_user)
    # ogr2'nin katilimi
    baska_k = DenemeKatilim.query.filter_by(toplam_net=50.0).first()
    client = app.test_client()
    token = _token(client, 'ogr_den')
    resp = client.get(f'/api/v1/denemeler/{baska_k.id}',
                       headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 404


def test_denemeler_tokensiz_401(app, db_session, admin_user):
    client = app.test_client()
    resp = client.get('/api/v1/denemeler')
    assert resp.status_code == 401
