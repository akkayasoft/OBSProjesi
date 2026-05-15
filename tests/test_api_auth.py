"""Mobil API — JWT kimlik dogrulama testleri (/api/v1)."""


def test_login_basarili_token_doner(app, db_session, admin_user):
    client = app.test_client()
    resp = client.post('/api/v1/auth/login', json={
        'kullanici_adi': 'test_admin', 'sifre': 'test12345',
    })
    assert resp.status_code == 200
    veri = resp.get_json()
    assert veri['basarili'] is True
    assert 'token' in veri['veri']
    assert veri['veri']['kullanici']['rol'] == 'admin'


def test_login_yanlis_sifre_401(app, db_session, admin_user):
    client = app.test_client()
    resp = client.post('/api/v1/auth/login', json={
        'kullanici_adi': 'test_admin', 'sifre': 'yanlis',
    })
    assert resp.status_code == 401
    assert resp.get_json()['basarili'] is False


def test_login_eksik_alan_400(app, db_session, admin_user):
    client = app.test_client()
    resp = client.post('/api/v1/auth/login', json={'kullanici_adi': 'x'})
    assert resp.status_code == 400


def test_me_token_ile_calisir(app, db_session, admin_user):
    client = app.test_client()
    login = client.post('/api/v1/auth/login', json={
        'kullanici_adi': 'test_admin', 'sifre': 'test12345',
    })
    token = login.get_json()['veri']['token']

    resp = client.get('/api/v1/me',
                       headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200
    assert resp.get_json()['veri']['kullanici']['id'] == admin_user.id


def test_me_tokensiz_401(app, db_session, admin_user):
    client = app.test_client()
    resp = client.get('/api/v1/me')
    assert resp.status_code == 401


def test_me_gecersiz_token_401(app, db_session, admin_user):
    client = app.test_client()
    resp = client.get('/api/v1/me',
                       headers={'Authorization': 'Bearer cok.gecersiz.token'})
    assert resp.status_code == 401
