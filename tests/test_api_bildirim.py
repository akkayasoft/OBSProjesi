"""Mobil API — Bildirim ve Duyuru endpoint testleri (Faz 2)."""


def _token(client):
    r = client.post('/api/v1/auth/login', json={
        'kullanici_adi': 'test_admin', 'sifre': 'test12345',
    })
    return r.get_json()['veri']['token']


def _hdr(token):
    return {'Authorization': f'Bearer {token}'}


def test_bildirim_listesi_ve_okunmamis_sayisi(app, db_session, admin_user):
    from app.models.bildirim import Bildirim
    for i in range(3):
        db_session.add(Bildirim(
            kullanici_id=admin_user.id, baslik=f'B{i}',
            mesaj='test mesaji', tur='bilgi', kategori='sistem',
        ))
    db_session.commit()

    client = app.test_client()
    token = _token(client)
    resp = client.get('/api/v1/bildirimler', headers=_hdr(token))
    assert resp.status_code == 200
    veri = resp.get_json()
    assert len(veri['veri']) == 3
    assert veri['okunmamis'] == 3


def test_bildirim_okundu_isaretleme(app, db_session, admin_user):
    from app.models.bildirim import Bildirim
    b = Bildirim(kullanici_id=admin_user.id, baslik='X',
                 mesaj='m', tur='bilgi', kategori='sistem')
    db_session.add(b)
    db_session.commit()

    client = app.test_client()
    token = _token(client)
    resp = client.post(f'/api/v1/bildirimler/{b.id}/okundu',
                        headers=_hdr(token))
    assert resp.status_code == 200
    db_session.refresh(b)
    assert b.okundu is True


def test_bildirim_tumunu_okundu(app, db_session, admin_user):
    from app.models.bildirim import Bildirim
    for i in range(4):
        db_session.add(Bildirim(
            kullanici_id=admin_user.id, baslik=f'B{i}',
            mesaj='m', tur='bilgi', kategori='sistem'))
    db_session.commit()

    client = app.test_client()
    token = _token(client)
    resp = client.post('/api/v1/bildirimler/tumunu-okundu',
                        headers=_hdr(token))
    assert resp.status_code == 200
    assert resp.get_json()['veri']['okundu_isaretlenen'] == 4
    assert Bildirim.okunmamis_sayisi(admin_user.id) == 0


def test_baskasinin_bildirimi_okunamaz(app, db_session, admin_user):
    """Kullanici baska birinin bildirimini okundu yapamaz."""
    from app.models.user import User
    from app.models.bildirim import Bildirim
    baska = User(username='baska', email='b@test.local',
                 ad='B', soyad='K', rol='ogrenci', aktif=True)
    baska.set_password('x')
    db_session.add(baska)
    db_session.commit()
    b = Bildirim(kullanici_id=baska.id, baslik='Gizli',
                 mesaj='m', tur='bilgi', kategori='sistem')
    db_session.add(b)
    db_session.commit()

    client = app.test_client()
    token = _token(client)
    resp = client.post(f'/api/v1/bildirimler/{b.id}/okundu',
                        headers=_hdr(token))
    assert resp.status_code == 404


def test_duyuru_listesi(app, db_session, admin_user):
    from app.models.duyurular import Duyuru
    db_session.add(Duyuru(
        baslik='Genel Duyuru', icerik='Herkese acik',
        kategori='genel', oncelik='normal', hedef_kitle='tumu',
        yayinlayan_id=admin_user.id, aktif=True,
    ))
    db_session.commit()

    client = app.test_client()
    token = _token(client)
    resp = client.get('/api/v1/duyurular', headers=_hdr(token))
    assert resp.status_code == 200
    veri = resp.get_json()['veri']
    assert len(veri) == 1
    assert veri[0]['baslik'] == 'Genel Duyuru'
    assert veri[0]['okundu'] is False


def test_duyuru_detay_okundu_kaydeder(app, db_session, admin_user):
    from app.models.duyurular import Duyuru
    d = Duyuru(baslik='D', icerik='i', kategori='genel',
               oncelik='normal', hedef_kitle='tumu',
               yayinlayan_id=admin_user.id, aktif=True)
    db_session.add(d)
    db_session.commit()

    client = app.test_client()
    token = _token(client)
    resp = client.get(f'/api/v1/duyurular/{d.id}', headers=_hdr(token))
    assert resp.status_code == 200
    assert resp.get_json()['veri']['okundu'] is True
    assert d.kullanici_okudu_mu(admin_user.id) is True


def test_bildirimler_tokensiz_401(app, db_session, admin_user):
    client = app.test_client()
    resp = client.get('/api/v1/bildirimler')
    assert resp.status_code == 401
