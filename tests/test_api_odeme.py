"""Mobil API — Odeme / borc durumu testleri (Faz 4)."""
from datetime import date
from decimal import Decimal


def _ogrenci_plan_kur(db_session):
    """Ogrenci user + Ogrenci + OdemePlani (9000 TL) + 3 taksit
    (biri odenmis)."""
    from app.models.user import User
    from app.models.muhasebe import Ogrenci, OdemePlani, Taksit

    u = User(username='ogr_ode', email='ogrode@test.local',
             ad='Can', soyad='Borc', rol='ogrenci', aktif=True)
    u.set_password('test12345')
    db_session.add(u)
    db_session.commit()

    ogr = Ogrenci(ogrenci_no='O200', ad='Can', soyad='Borc',
                  tc_kimlik='22200000000', cinsiyet='erkek',
                  sinif='10-B', aktif=True, user_id=u.id)
    db_session.add(ogr)
    db_session.commit()

    plan = OdemePlani(ogrenci_id=ogr.id, donem='2025-2026',
                      toplam_tutar=Decimal('9000'),
                      indirim_tutar=Decimal('0'),
                      taksit_sayisi=3, durum='aktif')
    db_session.add(plan)
    db_session.commit()

    # 1. taksit tam odenmis, digerleri beklemede
    db_session.add(Taksit(
        odeme_plani_id=plan.id, taksit_no=1, tutar=Decimal('3000'),
        vade_tarihi=date(2026, 5, 1), odenen_tutar=Decimal('3000'),
        durum='odendi'))
    db_session.add(Taksit(
        odeme_plani_id=plan.id, taksit_no=2, tutar=Decimal('3000'),
        vade_tarihi=date(2026, 6, 1), odenen_tutar=Decimal('0'),
        durum='beklemede'))
    db_session.add(Taksit(
        odeme_plani_id=plan.id, taksit_no=3, tutar=Decimal('3000'),
        vade_tarihi=date(2026, 7, 1), odenen_tutar=Decimal('0'),
        durum='beklemede'))
    db_session.commit()
    return u, ogr, plan


def _token(client, kullanici, sifre='test12345'):
    r = client.post('/api/v1/auth/login', json={
        'kullanici_adi': kullanici, 'sifre': sifre})
    return r.get_json()['veri']['token']


def test_ogrenci_borc_ozeti_dogru(app, db_session, admin_user):
    _ogrenci_plan_kur(db_session)
    client = app.test_client()
    token = _token(client, 'ogr_ode')
    resp = client.get('/api/v1/odemeler',
                       headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200
    veri = resp.get_json()['veri']
    assert veri['ozet']['toplam_borc'] == 9000.0
    assert veri['ozet']['odenen'] == 3000.0
    assert veri['ozet']['kalan'] == 6000.0
    assert len(veri['planlar']) == 1
    assert len(veri['planlar'][0]['taksitler']) == 3


def test_taksit_durumlari_donuyor(app, db_session, admin_user):
    _ogrenci_plan_kur(db_session)
    client = app.test_client()
    token = _token(client, 'ogr_ode')
    resp = client.get('/api/v1/odemeler',
                       headers={'Authorization': f'Bearer {token}'})
    taksitler = resp.get_json()['veri']['planlar'][0]['taksitler']
    assert taksitler[0]['durum'] == 'odendi'
    assert taksitler[0]['kalan'] == 0.0
    assert taksitler[1]['kalan'] == 3000.0


def test_veli_cocugunun_borcunu_gorur(app, db_session, admin_user):
    from app.models.user import User
    from app.models.kayit import VeliBilgisi
    _, ogr, _ = _ogrenci_plan_kur(db_session)

    veli = User(username='veli_ode', email='velode@test.local',
                ad='Ali', soyad='Borc', rol='veli', aktif=True)
    veli.set_password('test12345')
    db_session.add(veli)
    db_session.commit()
    db_session.add(VeliBilgisi(
        ogrenci_id=ogr.id, ad='Ali', soyad='Borc',
        yakinlik='baba', telefon='0555', user_id=veli.id))
    db_session.commit()

    client = app.test_client()
    token = _token(client, 'veli_ode')
    resp = client.get('/api/v1/odemeler',
                       headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200
    assert resp.get_json()['veri']['ozet']['kalan'] == 6000.0


def test_ogrencisiz_hesap_404(app, db_session, admin_user):
    client = app.test_client()
    token = _token(client, 'test_admin')
    resp = client.get('/api/v1/odemeler',
                       headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 404


def test_odemeler_tokensiz_401(app, db_session, admin_user):
    client = app.test_client()
    resp = client.get('/api/v1/odemeler')
    assert resp.status_code == 401
