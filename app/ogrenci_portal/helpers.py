"""Ogrenci portal ortak yardimci fonksiyonlari.

Once user_id FK'si uzerinden eslestirme yapilir (kayit sirasinda baglanir).
Isim bazli eslestirme GUVENSIZ: ayni isimde birden fazla ogrenci olabilir
ve veli/ogrenci karismasina yol acabilir.
"""
from flask_login import current_user
from app.models.muhasebe import Ogrenci
from app.models.kayit import VeliBilgisi, OgrenciKayit


def get_current_ogrenci():
    """Mevcut kullaniciya ait ogrenci kaydini guvenli sekilde bul."""
    if not current_user.is_authenticated:
        return None

    if current_user.rol == 'veli':
        veli = VeliBilgisi.query.filter_by(user_id=current_user.id).first()
        if veli and veli.ogrenci and veli.ogrenci.aktif:
            return veli.ogrenci
        return None

    # Ogrenci veya admin icin user_id eslestirmesi
    return Ogrenci.query.filter_by(user_id=current_user.id, aktif=True).first()


def get_current_veli():
    """Mevcut kullanici veli ise VeliBilgisi kaydini dondur."""
    if not current_user.is_authenticated or current_user.rol != 'veli':
        return None
    return VeliBilgisi.query.filter_by(user_id=current_user.id).first()


def get_ogrenci_sube(ogrenci):
    """Ogrencinin aktif kaydindaki subeyi bul."""
    if not ogrenci:
        return None
    kayit = OgrenciKayit.query.filter_by(
        ogrenci_id=ogrenci.id, durum='aktif'
    ).first()
    return kayit.sube if kayit else None
