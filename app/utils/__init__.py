from functools import wraps
from flask import abort, flash, redirect, url_for, request
from flask_login import current_user


def role_required(*roles):
    """Belirtilen rollerden birine sahip olma zorunlulugu.

    Ozel durum: 'yonetici' rolu 'admin' rolunun hakki olan yerlere
    URL prefix'ine gore modul izni varsa erisebilir. Boylece mevcut
    @role_required('admin') dekoratorleri tek tek degistirilmeden
    yonetici de kendi izinli modullerine girer.

    Sistem-ozel moduller (kullanici, denetim, ayarlar) varsayilan olarak
    yoneticiye acilmaz (kurumsal preset icinde bile yok). Admin orada
    devam eder.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.giris'))

            # 1) Direkt rol eslesmesi
            if current_user.rol in roles:
                return f(*args, **kwargs)

            # 2) Admin sayfasina yonetici geliyorsa modul izni ile ac
            if current_user.rol == 'yonetici' and 'admin' in roles:
                from app.module_registry import url_to_modul_key
                modul_key = url_to_modul_key(request.path)
                if modul_key and current_user.can_access(modul_key):
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
