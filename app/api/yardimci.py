"""Mobil API — paylasilan yardimcilar.

Ogrenci/veli rolundeki API kullanicisini ilgili Ogrenci kaydina
baglar. Faz 3+ endpoint'leri (devamsizlik, odeme, deneme) bunu kullanir.
"""


def hedef_ogrenci(user):
    """API kullanicisina ait Ogrenci kaydini dondur.

    - ogrenci rolu  : kendi Ogrenci kaydi
    - veli rolu     : bagli oldugu ogrencinin kaydi
    Bulunamazsa None.
    """
    from app.models.muhasebe import Ogrenci
    if user.rol == 'ogrenci':
        return Ogrenci.query.filter_by(user_id=user.id).first()
    if user.rol == 'veli':
        from app.models.kayit import VeliBilgisi
        v = VeliBilgisi.query.filter_by(user_id=user.id).first()
        if v is not None:
            return Ogrenci.query.filter_by(id=v.ogrenci_id).first()
    return None


def ogrenci_ozet(ogrenci):
    """Ogrenci kaydinin mobil uygulamaya donulecek ozeti."""
    return {
        'id': ogrenci.id,
        'ad_soyad': getattr(ogrenci, 'tam_ad',
                            f'{ogrenci.ad} {ogrenci.soyad}'),
        'ogrenci_no': ogrenci.ogrenci_no,
        'sinif': getattr(ogrenci, 'aktif_sinif_sube', None)
        or ogrenci.sinif,
    }
