"""Mobil API — JWT kimlik dogrulama yardimcilari.

Bagimsiz Flutter mobil uygulamasi token tabanli kimlik dogrulama
kullanir (web'deki Flask-Login session'i yerine). Login endpoint'i
JWT uretir; sonraki istekler 'Authorization: Bearer <token>' tasir.
"""
import datetime
from functools import wraps

import jwt
from flask import request, jsonify, g, current_app

# Token gecerlilik suresi (gun) — mobil uygulamada uzun oturum
TOKEN_GECERLILIK_GUN = 30


def _tenant_slug():
    """Aktif tenant slug'i — tek-tenant modda sabit deger."""
    t = getattr(g, 'tenant', None)
    return getattr(t, 'slug', None) if t else '_single'


def token_olustur(user):
    """Kullanici icin imzali JWT token uret."""
    simdi = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        'sub': str(user.id),  # JWT 'sub' string olmali (PyJWT 2.10+)
        'rol': user.rol,
        'slug': _tenant_slug(),
        'iat': simdi,
        'exp': simdi + datetime.timedelta(days=TOKEN_GECERLILIK_GUN),
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'],
                      algorithm='HS256')


def token_coz(token):
    """JWT token'i dogrula ve coz; gecersiz/suresi dolmus ise None."""
    try:
        return jwt.decode(token, current_app.config['SECRET_KEY'],
                          algorithms=['HS256'])
    except jwt.PyJWTError:
        return None


def api_basarili(veri=None, **ek):
    """Standart basarili JSON yaniti."""
    cikti = {'basarili': True}
    if veri is not None:
        cikti['veri'] = veri
    cikti.update(ek)
    return jsonify(cikti)


def api_hata(mesaj, kod=400):
    """Standart hata JSON yaniti."""
    return jsonify({'basarili': False, 'hata': mesaj}), kod


def api_auth(f):
    """Endpoint icin gecerli JWT token zorunlulugu.

    Basarili ise g.api_user'a kullanici nesnesini koyar.
    """
    @wraps(f)
    def sarmal(*args, **kwargs):
        baslik = request.headers.get('Authorization', '')
        if not baslik.startswith('Bearer '):
            return api_hata('Yetkilendirme tokeni gerekli.', 401)
        token = baslik[7:].strip()
        payload = token_coz(token)
        if payload is None:
            return api_hata('Token gecersiz veya suresi dolmus.', 401)
        # Token baska bir tenant'a aitse reddet
        if payload.get('slug') != _tenant_slug():
            return api_hata('Token bu kuruma ait degil.', 401)
        from app.models.user import User
        try:
            user_id = int(payload.get('sub'))
        except (TypeError, ValueError):
            return api_hata('Token gecersiz.', 401)
        user = User.query.filter_by(id=user_id).first()
        if user is None or not user.aktif:
            return api_hata('Kullanici bulunamadi veya pasif.', 401)
        g.api_user = user
        return f(*args, **kwargs)
    return sarmal


def rol_gerekli(*roller):
    """api_auth sonrasi rol kisitlamasi dekoratoru."""
    def dekorator(f):
        @wraps(f)
        def sarmal(*args, **kwargs):
            user = getattr(g, 'api_user', None)
            if user is None or user.rol not in roller:
                return api_hata('Bu islem icin yetkiniz yok.', 403)
            return f(*args, **kwargs)
        return sarmal
    return dekorator
