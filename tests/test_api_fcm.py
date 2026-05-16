"""Mobil API — FCM cihaz token kaydi testleri."""


def _token(client):
    r = client.post('/api/v1/auth/login', json={
        'kullanici_adi': 'test_admin', 'sifre': 'test12345'})
    return r.get_json()['veri']['token']


def test_fcm_token_kaydedilir(app, db_session, admin_user):
    from app.models.bildirim import CihazTokeni
    client = app.test_client()
    jwt = _token(client)
    resp = client.post('/api/v1/fcm-token',
                        json={'token': 'cihaz-token-abc', 'platform': 'android'},
                        headers={'Authorization': f'Bearer {jwt}'})
    assert resp.status_code == 200
    kayit = CihazTokeni.query.filter_by(token='cihaz-token-abc').first()
    assert kayit is not None
    assert kayit.kullanici_id == admin_user.id
    assert kayit.platform == 'android'


def test_ayni_token_mukerrer_olmaz(app, db_session, admin_user):
    from app.models.bildirim import CihazTokeni
    client = app.test_client()
    jwt = _token(client)
    for _ in range(3):
        client.post('/api/v1/fcm-token',
                    json={'token': 'tekrar-token', 'platform': 'android'},
                    headers={'Authorization': f'Bearer {jwt}'})
    assert CihazTokeni.query.filter_by(token='tekrar-token').count() == 1


def test_fcm_token_eksik_400(app, db_session, admin_user):
    client = app.test_client()
    jwt = _token(client)
    resp = client.post('/api/v1/fcm-token', json={},
                        headers={'Authorization': f'Bearer {jwt}'})
    assert resp.status_code == 400


def test_fcm_token_tokensiz_401(app, db_session, admin_user):
    client = app.test_client()
    resp = client.post('/api/v1/fcm-token', json={'token': 'x'})
    assert resp.status_code == 401
