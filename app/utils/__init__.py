from functools import wraps
from flask import abort, flash, redirect, url_for, request
from flask_login import current_user


def role_required(*roles):
    """Belirtilen rollerden birine sahip olma zorunlulugu.

    NOT (mussteri istegi 2026-05-08): 'yonetici' rolu artik 'admin'
    ile esit yetkilere sahip. Admin'in girebildigi her yere yonetici
    de girebilir; modul_key veya URL prefix kontrolu yapilmadan
    dogrudan gecer. Tum @role_required('admin') dekoratorleri otomatik
    olarak yoneticiyi de kapsar.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.giris'))

            # 1) Direkt rol eslesmesi
            if current_user.rol in roles:
                return f(*args, **kwargs)

            # 2) Admin gerektiren yerlere yonetici de girebilir (admin esiti)
            if current_user.rol == 'yonetici' and 'admin' in roles:
                return f(*args, **kwargs)

            abort(403)
        return decorated_function
    return decorator


def modul_gerekli(modul_key: str):
    """Spesifik bir modul icin erisim kontrol dekoratoru.

    role_required'a kiyasla daha net: rol onemli degil, sadece
    'bu kullanici bu module erisebiliyor mu?' kontrol edilir.
    Yeni yazilan routelarda tercih edilebilir.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.giris'))
            if not current_user.can_access(modul_key):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
