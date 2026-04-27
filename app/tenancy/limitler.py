"""Tenant abonelik plani limitleri.

Her dershane bir plana abonedir; plan limitleri eklenebilir kayit sayilarini
kontrol eder. Ozel anlasmali musterilere Tenant tablosundaki override
alanlari (ogrenci_limiti, kullanici_limiti, ogretmen_limiti) kullanilarak
preset'ten farkli limitler verilebilir.

Sinirsiz plan icin: plan='unlimited' veya override alanlarinda None.
None: o ozellik icin limitsiz (plan preset default'u uygulanir).
0:    o ozellik icin tamamen yasak (kayit eklenemez).

Kullanim:
    from app.tenancy.limitler import (
        plan_limitleri, kullanici_limit_kontrol,
        ogrenci_limit_kontrol, ogretmen_limit_kontrol,
    )
    izin, mesaj = ogrenci_limit_kontrol()
    if not izin:
        flash(mesaj, 'danger')
        return redirect(...)
"""
from __future__ import annotations

from typing import Optional

from flask import g

# Plan kodu -> {ad, ogrenci, ogretmen, kullanici, fiyat_tl} ozeti
# fiyat satis dokumanlarinda kullanilmak icin; kod yalnizca limitleri okur.
PLAN_LIMITLERI: dict[str, dict] = {
    'basic': {
        'ad': 'Başlangıç',
        'aciklama': 'Küçük dershaneler için temel paket',
        'ogrenci_limiti': 100,
        'ogretmen_limiti': 10,
        'kullanici_limiti': 200,    # ogrenci+veli+ogretmen+yonetici toplam
        'fiyat_tl_aylik': 750,
    },
    'standart': {
        'ad': 'Standart',
        'aciklama': 'Orta ölçekli dershaneler',
        'ogrenci_limiti': 500,
        'ogretmen_limiti': 30,
        'kullanici_limiti': 1000,
        'fiyat_tl_aylik': 1750,
    },
    'premium': {
        'ad': 'Premium',
        'aciklama': 'Büyük dershane / lokal zincir',
        'ogrenci_limiti': 2000,
        'ogretmen_limiti': 100,
        'kullanici_limiti': 5000,
        'fiyat_tl_aylik': 3500,
    },
    'unlimited': {
        'ad': 'Sınırsız',
        'aciklama': 'Kurumsal — limitsiz',
        'ogrenci_limiti': None,
        'ogretmen_limiti': None,
        'kullanici_limiti': None,
        'fiyat_tl_aylik': None,
    },
}


def plan_limitleri(plan_kod: str | None) -> dict:
    """Plan kodundan limit dict'i dondurur. Bilinmiyorsa standart varsayar."""
    if plan_kod and plan_kod in PLAN_LIMITLERI:
        return PLAN_LIMITLERI[plan_kod]
    return PLAN_LIMITLERI['standart']


def _aktif_tenant():
    """Mevcut request'in tenant'i (g.tenant). None ise (CLI/script gibi)
    'limitsiz' davranis."""
    return getattr(g, 'tenant', None)


def _efektif_limit(tenant, alan: str) -> Optional[int]:
    """Tenant icin bir alanin (ogrenci_limiti / ogretmen_limiti /
    kullanici_limiti) etkin limit degerini hesapla:

    1. Tenant tablosundaki override (None degilse) kullanilir.
    2. Yoksa plan preset'inden okunur.
    3. None: limitsiz.
    """
    if tenant is None:
        return None

    override = getattr(tenant, alan, None)
    if override is not None:
        return override

    plan = getattr(tenant, 'plan', None) or 'standart'
    return plan_limitleri(plan).get(alan)


def _format_limit_uyarisi(tip: str, mevcut: int, limit: int, tenant) -> str:
    plan_ad = plan_limitleri(getattr(tenant, 'plan', None) or 'standart')['ad']
    return (f'⚠️ {tip} kayıt limiti aşıldı. Mevcut: {mevcut}, '
            f'Limit: {limit} ({plan_ad} plan). '
            f'Daha fazla kayıt eklemek için planınızı yükseltin '
            f'veya yöneticinizle iletişime geçin.')


def ogrenci_limit_kontrol() -> tuple[bool, str | None]:
    """Yeni ogrenci eklenebilir mi? (izin, hata_mesaji_or_none)."""
    from app.models.muhasebe import Ogrenci

    tenant = _aktif_tenant()
    limit = _efektif_limit(tenant, 'ogrenci_limiti')
    if limit is None:
        return True, None

    mevcut = Ogrenci.query.filter_by(aktif=True).count()
    if mevcut >= limit:
        return False, _format_limit_uyarisi('Öğrenci', mevcut, limit, tenant)
    return True, None


def ogretmen_limit_kontrol() -> tuple[bool, str | None]:
    """Yeni ogretmen/personel eklenebilir mi?"""
    from app.models.user import User

    tenant = _aktif_tenant()
    limit = _efektif_limit(tenant, 'ogretmen_limiti')
    if limit is None:
        return True, None

    mevcut = User.query.filter_by(rol='ogretmen', aktif=True).count()
    if mevcut >= limit:
        return False, _format_limit_uyarisi('Öğretmen', mevcut, limit, tenant)
    return True, None


def kullanici_limit_kontrol(yeni_rol: str | None = None) -> tuple[bool, str | None]:
    """Yeni kullanici (her rol) eklenebilir mi?

    yeni_rol: opsiyonel, eklenmek istenen rol (mesaj icin).
    """
    from app.models.user import User

    tenant = _aktif_tenant()
    limit = _efektif_limit(tenant, 'kullanici_limiti')
    if limit is None:
        return True, None

    mevcut = User.query.filter_by(aktif=True).count()
    if mevcut >= limit:
        return False, _format_limit_uyarisi('Toplam kullanıcı', mevcut, limit, tenant)
    return True, None


def kullanim_durumu() -> dict:
    """Mevcut tenant icin tum limit/kullanim ozetini dondurur (UI icin)."""
    from app.models.user import User
    from app.models.muhasebe import Ogrenci

    tenant = _aktif_tenant()
    plan_kod = getattr(tenant, 'plan', None) or 'standart'
    plan = plan_limitleri(plan_kod)

    aktif_ogrenci = Ogrenci.query.filter_by(aktif=True).count()
    aktif_ogretmen = User.query.filter_by(rol='ogretmen', aktif=True).count()
    aktif_kullanici = User.query.filter_by(aktif=True).count()

    def _orani(mevcut, limit):
        if limit is None or limit == 0:
            return None
        return round(min(100, (mevcut / limit) * 100), 1)

    return {
        'plan_kod': plan_kod,
        'plan_ad': plan['ad'],
        'plan_aciklama': plan.get('aciklama'),
        'ogrenci': {
            'mevcut': aktif_ogrenci,
            'limit': _efektif_limit(tenant, 'ogrenci_limiti'),
            'oran': _orani(aktif_ogrenci, _efektif_limit(tenant, 'ogrenci_limiti')),
        },
        'ogretmen': {
            'mevcut': aktif_ogretmen,
            'limit': _efektif_limit(tenant, 'ogretmen_limiti'),
            'oran': _orani(aktif_ogretmen, _efektif_limit(tenant, 'ogretmen_limiti')),
        },
        'kullanici': {
            'mevcut': aktif_kullanici,
            'limit': _efektif_limit(tenant, 'kullanici_limiti'),
            'oran': _orani(aktif_kullanici, _efektif_limit(tenant, 'kullanici_limiti')),
        },
    }
