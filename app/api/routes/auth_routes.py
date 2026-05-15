"""Mobil API — kimlik dogrulama endpoint'leri."""
from flask import request, g

from app.api.auth import (token_olustur, api_basarili, api_hata, api_auth,
                          TOKEN_GECERLILIK_GUN)


def kullanici_ozet(user):
    """Mobil uygulamaya donulecek kullanici ozeti."""
    return {
        'id': user.id,
        'ad': user.ad,
        'soyad': user.soyad,
        'tam_ad': getattr(user, 'tam_ad', f'{user.ad} {user.soyad}'),
        'rol': user.rol,
        'rol_adi': getattr(user, 'rol_str', user.rol),
        'email': user.email,
    }


def register(bp):

    @bp.route('/auth/login', methods=['POST'])
    def login():
        """Kullanici adi + sifre -> JWT token.

        Tenant (kurum) cagrilan subdomain'den cozulur.
        """
        veri = request.get_json(silent=True) or {}
        kullanici_adi = (veri.get('kullanici_adi')
                         or veri.get('username') or '').strip()
        sifre = veri.get('sifre') or veri.get('password') or ''
        if not kullanici_adi or not sifre:
            return api_hata('Kullanici adi ve sifre gerekli.', 400)

        from app.models.user import User
        user = User.query.filter(
            (User.username == kullanici_adi)
            | (User.email == kullanici_adi)
        ).first()
        if user is None or not user.check_password(sifre):
            return api_hata('Kullanici adi veya sifre hatali.', 401)
        if not user.aktif:
            return api_hata('Hesabiniz pasif durumda.', 403)

        token = token_olustur(user)
        return api_basarili({
            'token': token,
            'gecerlilik_gun': TOKEN_GECERLILIK_GUN,
            'kullanici': kullanici_ozet(user),
        })

    @bp.route('/me', methods=['GET'])
    @api_auth
    def me():
        """Gecerli token'in sahibi kullanicinin bilgisi (token testi)."""
        return api_basarili({'kullanici': kullanici_ozet(g.api_user)})
