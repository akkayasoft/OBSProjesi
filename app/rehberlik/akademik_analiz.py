"""Deneme sinavi sonuclarindan kural-tabanli rehberlik analizi.

Bu modul LLM degil; kurum icin acik/kontrol edilebilir olsun diye basit
esik kurallari uzerine kurulu. Rehber ogretmen hangi oneriyi kimin
gordugunu tahmin edebilir ve tesvik/uyari metinlerini ihtiyaca gore
genisletebilir.

Kullanim:
    from app.rehberlik.akademik_analiz import ogrenci_analizi
    analiz = ogrenci_analizi(ogrenci_id)

Cikti sozluk yapisi:
    {
        'katilim_sayisi': int,
        'son_katilimlar': [DenemeKatilim, ...],     # en yeni < tarih >
        'ortalama_puan': float | None,
        'ortalama_net': float | None,
        'trend': 'yukseliyor' | 'dusuyor' | 'sabit' | None,
        'trend_fark': float | None,                  # son puan - onceki puan
        'seviye_kiyas': 'ustunde' | 'ortalama' | 'altinda' | None,
        'yuzdelik_dilim': int | None,                # 1..100, 1 = en iyi
        'en_zayif_dersler': [ {ders, benim_net, seviye_ort, fark}, ... ],
        'en_guclu_dersler': [ ... ],
        'oneriler': [ {tur: 'basari'|'uyari'|'bilgi', mesaj: str, ikon: str}, ... ],
    }

Hicbir katilim yoksa:
    {'katilim_sayisi': 0, 'oneriler': []}
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func

from app.extensions import db
from app.models.deneme_sinavi import (DenemeKatilim, DenemeDersSonucu,
                                      DenemeDersi, DenemeSinavi)


# --- Yardimci hesaplar ----------------------------------------------------

def _ortalama(degerler: list[float | int | None]) -> float | None:
    temiz = [v for v in degerler if v is not None]
    if not temiz:
        return None
    return sum(temiz) / len(temiz)


def _seviye_puan_ortalamasi(sinav_id: int) -> float | None:
    """Bir deneme sinavina katilan tum ogrencilerin puan ortalamasi."""
    val = (db.session.query(func.avg(DenemeKatilim.toplam_puan))
           .filter(DenemeKatilim.deneme_sinavi_id == sinav_id,
                   DenemeKatilim.toplam_puan.isnot(None))
           .scalar())
    return float(val) if val is not None else None


def _yuzdelik_dilim(katilim: DenemeKatilim) -> int | None:
    """Aynı denemede ogrenci yuzdelik dilim (1 = en iyi)."""
    if katilim.toplam_puan is None:
        return None
    toplam = (DenemeKatilim.query
              .filter(DenemeKatilim.deneme_sinavi_id == katilim.deneme_sinavi_id,
                      DenemeKatilim.toplam_puan.isnot(None))
              .count())
    if toplam == 0:
        return None
    ustte = (DenemeKatilim.query
             .filter(DenemeKatilim.deneme_sinavi_id == katilim.deneme_sinavi_id,
                     DenemeKatilim.toplam_puan > katilim.toplam_puan)
             .count())
    # yuzdelik dilim: ustte olanlarin + 1'in toplama orani
    return max(1, min(100, int(((ustte + 1) / toplam) * 100)))


def _ders_seviye_ortalamasi(deneme_dersi_id: int) -> float | None:
    val = (db.session.query(func.avg(DenemeDersSonucu.net))
           .filter(DenemeDersSonucu.deneme_dersi_id == deneme_dersi_id,
                   DenemeDersSonucu.net.isnot(None))
           .scalar())
    return float(val) if val is not None else None


# --- Ana analiz -----------------------------------------------------------

SON_N = 5  # Son kac denemeyi analiz edelim


def ogrenci_analizi(ogrenci_id: int) -> dict[str, Any]:
    """Bir ogrenci icin son denemeler uzerinden kural-tabanli analiz."""
    katilimlar = (DenemeKatilim.query
                  .join(DenemeSinavi, DenemeKatilim.deneme_sinavi_id == DenemeSinavi.id)
                  .filter(DenemeKatilim.ogrenci_id == ogrenci_id,
                          DenemeKatilim.katildi == True,  # noqa: E712
                          DenemeSinavi.durum.in_(('uygulandi', 'tamamlandi')))
                  .order_by(DenemeSinavi.tarih.desc())
                  .limit(SON_N)
                  .all())

    if not katilimlar:
        return {
            'katilim_sayisi': 0,
            'son_katilimlar': [],
            'oneriler': [],
        }

    ortalama_puan = _ortalama([k.toplam_puan for k in katilimlar])
    ortalama_net = _ortalama([k.toplam_net for k in katilimlar])

    # Trend: en son iki denemenin puan farki
    trend, trend_fark = None, None
    puanli = [k for k in katilimlar if k.toplam_puan is not None]
    if len(puanli) >= 2:
        son, onceki = puanli[0], puanli[1]
        diff = (son.toplam_puan or 0) - (onceki.toplam_puan or 0)
        trend_fark = round(diff, 2)
        if diff > 5:
            trend = 'yukseliyor'
        elif diff < -5:
            trend = 'dusuyor'
        else:
            trend = 'sabit'

    # Seviye kiyasi (en son denemede)
    seviye_kiyas = None
    yuzdelik = None
    son_katilim = katilimlar[0]
    seviye_ort = _seviye_puan_ortalamasi(son_katilim.deneme_sinavi_id)
    if seviye_ort is not None and son_katilim.toplam_puan is not None:
        if son_katilim.toplam_puan > seviye_ort + 5:
            seviye_kiyas = 'ustunde'
        elif son_katilim.toplam_puan < seviye_ort - 5:
            seviye_kiyas = 'altinda'
        else:
            seviye_kiyas = 'ortalama'
        yuzdelik = _yuzdelik_dilim(son_katilim)

    # Ders bazli analiz: son denemedeki derslere bak
    en_zayif: list[dict] = []
    en_guclu: list[dict] = []
    son_sonuclar = son_katilim.ders_sonuclari.all()
    for s in son_sonuclar:
        d = s.ders
        if not d or s.net is None:
            continue
        seviye_ders_ort = _ders_seviye_ortalamasi(d.id)
        fark = None if seviye_ders_ort is None else round((s.net or 0) - seviye_ders_ort, 2)
        veri = {
            'ders_adi': d.ders_adi,
            'ders_kodu': d.ders_kodu,
            'benim_net': round(s.net or 0, 2),
            'seviye_ort': round(seviye_ders_ort, 2) if seviye_ders_ort is not None else None,
            'fark': fark,
            'soru_sayisi': d.soru_sayisi,
            'basari_orani': (
                round(((s.net or 0) / d.soru_sayisi) * 100, 1)
                if d.soru_sayisi else None
            ),
        }
        if fark is not None:
            if fark < -2:  # seviyenin 2 net altinda
                en_zayif.append(veri)
            elif fark > 2:
                en_guclu.append(veri)
    en_zayif.sort(key=lambda x: x['fark'])       # en negatiften en azalana
    en_guclu.sort(key=lambda x: -(x['fark'] or 0))  # en buyukten azalana
    en_zayif = en_zayif[:3]
    en_guclu = en_guclu[:3]

    # Kural-tabanli oneriler
    oneriler = _oneriler_uret(
        katilim_sayisi=len(katilimlar),
        trend=trend,
        trend_fark=trend_fark,
        seviye_kiyas=seviye_kiyas,
        yuzdelik=yuzdelik,
        en_zayif=en_zayif,
        en_guclu=en_guclu,
        son_katilim=son_katilim,
    )

    return {
        'katilim_sayisi': len(katilimlar),
        'son_katilimlar': katilimlar,
        'ortalama_puan': round(ortalama_puan, 2) if ortalama_puan is not None else None,
        'ortalama_net': round(ortalama_net, 2) if ortalama_net is not None else None,
        'trend': trend,
        'trend_fark': trend_fark,
        'seviye_kiyas': seviye_kiyas,
        'yuzdelik_dilim': yuzdelik,
        'en_zayif_dersler': en_zayif,
        'en_guclu_dersler': en_guclu,
        'oneriler': oneriler,
    }


def _oneriler_uret(*, katilim_sayisi, trend, trend_fark, seviye_kiyas,
                   yuzdelik, en_zayif, en_guclu, son_katilim) -> list[dict]:
    """Kural esikleri -> insan-okur-yazar oneriler."""
    oneriler: list[dict] = []

    # Trend tabanli
    if trend == 'yukseliyor':
        oneriler.append({
            'tur': 'basari',
            'ikon': 'bi-graph-up-arrow',
            'mesaj': (f'Son denemede puani {trend_fark:+.1f} artti. '
                      'Mevcut calisma planini surdurmesi tesvik edilebilir.'),
        })
    elif trend == 'dusuyor':
        oneriler.append({
            'tur': 'uyari',
            'ikon': 'bi-graph-down-arrow',
            'mesaj': (f'Son denemede puani {trend_fark:+.1f} dustu. '
                      'Ogrenci ile bireysel gorusme planlanmasi faydali olabilir. '
                      'Calisma programi, uyku ve motivasyon kontrol edilmeli.'),
        })

    # Seviye kiyasi
    if seviye_kiyas == 'altinda':
        oneriler.append({
            'tur': 'uyari',
            'ikon': 'bi-exclamation-triangle',
            'mesaj': ('Son denemede seviye ortalamasinin altinda kaldi. '
                      'Etut/odev destegi ve hedef belirleme calismasi onerilir.'),
        })
    elif seviye_kiyas == 'ustunde':
        oneriler.append({
            'tur': 'basari',
            'ikon': 'bi-trophy',
            'mesaj': ('Seviye ortalamasinin uzerinde — guclu yanlarini '
                      'pekistirip zorluk seviyesi yuksek sorulara yonlendirin.'),
        })

    # Yuzdelik dilim uyarisi
    if yuzdelik is not None:
        if yuzdelik <= 10:
            oneriler.append({
                'tur': 'basari',
                'ikon': 'bi-award',
                'mesaj': f'Seviyede ilk %{yuzdelik}\'lik dilimde. Hedef yuksek tutulabilir.',
            })
        elif yuzdelik >= 80:
            oneriler.append({
                'tur': 'uyari',
                'ikon': 'bi-hourglass-split',
                'mesaj': (f'Seviyede alt %{100-yuzdelik}\'lik kisimda (dilim {yuzdelik}). '
                          'Temel eksikler icin ders bazli tekrar programi planlayin.'),
            })

    # Zayif dersler
    if en_zayif:
        isimler = ', '.join(z['ders_adi'] for z in en_zayif)
        oneriler.append({
            'tur': 'uyari',
            'ikon': 'bi-book',
            'mesaj': (f'Seviye altinda kalan dersler: {isimler}. '
                      'Bu derslerde konu eksiklerini tespit edip '
                      'bireysel etut/kaynak destegi verin.'),
        })

    # Guclu dersler
    if en_guclu:
        isimler = ', '.join(g['ders_adi'] for g in en_guclu)
        oneriler.append({
            'tur': 'bilgi',
            'ikon': 'bi-stars',
            'mesaj': (f'Guclu yanlari: {isimler}. '
                      'Bu alanlarda ogrenci akademik ozgueven kazanabilir, '
                      'meslek/bolum tercihlerinde dikkate alinabilir.'),
        })

    # Genel bilgi
    if katilim_sayisi < 2:
        oneriler.append({
            'tur': 'bilgi',
            'ikon': 'bi-info-circle',
            'mesaj': ('Henuz tek deneme sonucu var; trend analizi icin en az 2-3 '
                      'deneme verisi gereklidir.'),
        })

    # Hicbir oneri tetiklenmediyse genel mesaj
    if not oneriler:
        oneriler.append({
            'tur': 'bilgi',
            'ikon': 'bi-check-circle',
            'mesaj': ('Sonuclar dengeli. Mevcut calisma disiplinin surmesi '
                      'icin ogrenciyi tesvik edin.'),
        })

    return oneriler


# --- Risk listesi (dashboard icin) ----------------------------------------

def risk_altindaki_ogrenciler(limit: int = 10) -> list[dict]:
    """Son denemede alt %20'de olan veya puanı peş peşe düşen öğrenciler."""
    from app.models.muhasebe import Ogrenci

    # Her ogrencinin en son deneme katilimi
    son_katilimlar = (db.session.query(
        DenemeKatilim.ogrenci_id,
        func.max(DenemeKatilim.id).label('son_id'))
        .group_by(DenemeKatilim.ogrenci_id)
        .subquery())

    katilimlar = (DenemeKatilim.query
                  .join(son_katilimlar, DenemeKatilim.id == son_katilimlar.c.son_id)
                  .filter(DenemeKatilim.toplam_puan.isnot(None))
                  .all())

    risk: list[dict] = []
    for k in katilimlar:
        if not k.ogrenci or not k.ogrenci.aktif:
            continue
        seviye_ort = _seviye_puan_ortalamasi(k.deneme_sinavi_id)
        yuzdelik = _yuzdelik_dilim(k)
        risk_skoru = 0
        nedenler = []

        if yuzdelik is not None and yuzdelik >= 80:
            risk_skoru += 2
            nedenler.append(f'Dilim {yuzdelik}')
        if seviye_ort is not None and (k.toplam_puan or 0) < seviye_ort - 10:
            risk_skoru += 1
            nedenler.append(f'Seviye ort. {seviye_ort:.1f} altinda')

        # Trend kontrolu: son iki katilim
        onceki = (DenemeKatilim.query
                  .filter(DenemeKatilim.ogrenci_id == k.ogrenci_id,
                          DenemeKatilim.id != k.id,
                          DenemeKatilim.toplam_puan.isnot(None))
                  .order_by(DenemeKatilim.id.desc())
                  .first())
        if onceki and (k.toplam_puan or 0) < (onceki.toplam_puan or 0) - 10:
            risk_skoru += 2
            nedenler.append('Puan dustu')

        if risk_skoru >= 2:
            risk.append({
                'ogrenci': k.ogrenci,
                'son_puan': k.toplam_puan,
                'seviye_ort': seviye_ort,
                'yuzdelik': yuzdelik,
                'risk_skoru': risk_skoru,
                'nedenler': nedenler,
                'son_sinav': k.sinav,
                'katilim_id': k.id,
            })

    risk.sort(key=lambda x: -x['risk_skoru'])
    return risk[:limit]
