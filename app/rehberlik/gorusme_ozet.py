"""Otomatik gorusme baglam ozeti.

Yeni gorusme acilirken rehber ogretmen ogrenci hakkinda 'son durumu' tek bakista
gorebilsin diye uretilen kisa bir baglam karti. Goal: rehberin notlari
yazmadan once bakacagi pano.

Kullanim:
    from app.rehberlik.gorusme_ozet import gorusme_baglam_ozeti
    ozet = gorusme_baglam_ozeti(ogrenci_id)

Cikti:
    {
        'ogrenci': Ogrenci | None,
        'risk': {... ogrenci_risk_skoru ciktisi ...},
        'son_gorusme': Gorusme | None,
        'son_gorusme_gunluk': int | None,         # son gorusmeden bu yana gun
        'devamsizlik_30g': int,
        'olumsuz_davranis_14g': int,
        'son_3_deneme': [
            {'sinav_ad': str, 'tarih': date, 'puan': float|None, 'net': float|None},
            ...
        ],
        'aktif_plan_var': bool,
        'oneri_konular': [str, ...],              # form 'konu' alanina dropdown gibi
        'metin': str,                             # textarea'a kopyalanmaya hazir
    }
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.models.deneme_sinavi import DenemeKatilim, DenemeSinavi
from app.models.devamsizlik import Devamsizlik
from app.models.muhasebe import Ogrenci
from app.models.rehberlik import (DavranisKaydi, Gorusme, OgrenciProfil,
                                  RehberlikPlani)
from app.rehberlik.risk_skoru import ogrenci_risk_skoru


def gorusme_baglam_ozeti(ogrenci_id: int) -> dict[str, Any]:
    bugun = date.today()
    ogrenci = Ogrenci.query.get(ogrenci_id)
    if not ogrenci:
        return {'ogrenci': None}

    risk = ogrenci_risk_skoru(ogrenci_id, bugun=bugun)

    # Son gorusme
    son_gorusme = (Gorusme.query
                   .filter_by(ogrenci_id=ogrenci_id, durum='tamamlandi')
                   .order_by(Gorusme.gorusme_tarihi.desc())
                   .first())
    son_gorusme_gunluk = None
    if son_gorusme:
        delta = bugun - son_gorusme.gorusme_tarihi.date()
        son_gorusme_gunluk = delta.days

    # 30 gunluk devamsizlik (gun sayisi)
    devamsizlik_30g = risk.get('detay', {}).get('devamsizlik', {}).get('gun_sayisi', 0)

    # 14 gunluk olumsuz davranis
    olumsuz_14g = risk.get('detay', {}).get('davranis', {}).get('olumsuz_sayi', 0)

    # Son 3 deneme
    son_3 = (DenemeKatilim.query
             .join(DenemeSinavi, DenemeKatilim.deneme_sinavi_id == DenemeSinavi.id)
             .filter(DenemeKatilim.ogrenci_id == ogrenci_id,
                     DenemeKatilim.katildi == True,  # noqa: E712
                     DenemeSinavi.durum.in_(('uygulandi', 'tamamlandi')))
             .order_by(DenemeSinavi.tarih.desc())
             .limit(3)
             .all())
    son_3_deneme = []
    for k in son_3:
        son_3_deneme.append({
            'sinav_ad': k.sinav.ad if k.sinav else '—',
            'tarih': k.sinav.tarih if k.sinav else None,
            'puan': float(k.toplam_puan) if k.toplam_puan is not None else None,
            'net': float(k.toplam_net) if k.toplam_net is not None else None,
        })

    # Aktif plan
    aktif_plan = (RehberlikPlani.query
                  .filter_by(ogrenci_id=ogrenci_id, durum='aktif')
                  .first())

    # Profil
    profil = OgrenciProfil.query.filter_by(ogrenci_id=ogrenci_id).first()

    # Oneri konular: kural-tabanli olası gorusme baslıkları
    oneri_konular = _oneri_konular(
        risk=risk,
        devamsizlik_30g=devamsizlik_30g,
        olumsuz_14g=olumsuz_14g,
        son_gorusme_gunluk=son_gorusme_gunluk,
        aktif_plan=aktif_plan,
    )

    # Hazır textarea metni
    metin = _baglam_metni(
        ogrenci=ogrenci,
        risk=risk,
        devamsizlik_30g=devamsizlik_30g,
        olumsuz_14g=olumsuz_14g,
        son_3_deneme=son_3_deneme,
        son_gorusme=son_gorusme,
        son_gorusme_gunluk=son_gorusme_gunluk,
        aktif_plan=aktif_plan,
        profil=profil,
    )

    return {
        'ogrenci': ogrenci,
        'risk': risk,
        'son_gorusme': son_gorusme,
        'son_gorusme_gunluk': son_gorusme_gunluk,
        'devamsizlik_30g': devamsizlik_30g,
        'olumsuz_davranis_14g': olumsuz_14g,
        'son_3_deneme': son_3_deneme,
        'aktif_plan': aktif_plan,
        'aktif_plan_var': aktif_plan is not None,
        'oneri_konular': oneri_konular,
        'metin': metin,
    }


def _oneri_konular(*, risk, devamsizlik_30g, olumsuz_14g,
                   son_gorusme_gunluk, aktif_plan) -> list[str]:
    konular: list[str] = []

    if devamsizlik_30g >= 4:
        konular.append('Devamsizlik degerlendirmesi')
    if olumsuz_14g >= 2:
        konular.append('Davranissal destek gorusmesi')

    deneme = risk.get('detay', {}).get('deneme', {}) if risk else {}
    if deneme.get('trend') == 'dusuyor':
        konular.append('Akademik dusus uzerine bireysel gorusme')
    if deneme.get('son_yuzdelik') and deneme['son_yuzdelik'] >= 80:
        konular.append('Calisma plani ve hedef belirleme')

    if risk.get('seviye') == 'yuksek':
        konular.append('Erken uyari: kapsamli risk degerlendirmesi')

    if son_gorusme_gunluk is not None and son_gorusme_gunluk >= 60:
        konular.append('Periyodik takip gorusmesi')
    elif son_gorusme_gunluk is None:
        konular.append('Tanisma / ilk gorusme')

    if not aktif_plan and risk.get('seviye') in ('orta', 'yuksek'):
        konular.append('Rehberlik plani olusturma')

    if not konular:
        konular.append('Genel takip gorusmesi')

    return konular


def _baglam_metni(*, ogrenci, risk, devamsizlik_30g, olumsuz_14g,
                  son_3_deneme, son_gorusme, son_gorusme_gunluk,
                  aktif_plan, profil) -> str:
    """Textarea'a bir tikla kopyalanmaya hazir baglam ozeti."""
    satirlar: list[str] = []
    satirlar.append(f"--- OTOMATIK BAGLAM OZETI ({date.today().strftime('%d.%m.%Y')}) ---")
    satirlar.append(f"Ogrenci: {ogrenci.tam_ad} ({ogrenci.ogrenci_no})")
    if ogrenci.aktif_sinif_sube:
        satirlar.append(f"Sinif/Sube: {ogrenci.aktif_sinif_sube}")

    # Risk
    skor = risk.get('skor', 0)
    seviye = risk.get('seviye', 'dusuk')
    sebepler = risk.get('sebepler', [])
    satirlar.append(f"Risk skoru: {skor}/100 ({seviye})")
    if sebepler:
        satirlar.append("  Sinyaller: " + "; ".join(sebepler))

    # Devamsizlik / davranis
    satirlar.append(f"Devamsizlik (son 30g): {devamsizlik_30g} gun")
    satirlar.append(f"Olumsuz davranis (son 14g): {olumsuz_14g} kayit")

    # Son 3 deneme
    if son_3_deneme:
        satirlar.append("Son denemeler:")
        for d in son_3_deneme:
            tarih_str = d['tarih'].strftime('%d.%m.%Y') if d['tarih'] else '—'
            puan_str = f"{d['puan']:.1f}p" if d['puan'] is not None else '—'
            net_str = f"{d['net']:.1f} net" if d['net'] is not None else ''
            satirlar.append(f"  - {tarih_str} {d['sinav_ad']}: {puan_str} {net_str}".rstrip())

    # Onceki gorusme
    if son_gorusme:
        satirlar.append(
            f"Son tamamlanan gorusme: {son_gorusme.gorusme_tarihi.strftime('%d.%m.%Y')} "
            f"({son_gorusme_gunluk} gun once) - \"{son_gorusme.konu}\""
        )
    else:
        satirlar.append("Daha once tamamlanmis gorusme yok.")

    # Aktif plan
    if aktif_plan:
        satirlar.append(f"Aktif rehberlik plani: \"{aktif_plan.baslik}\"")

    # Profil flag'leri
    if profil:
        flag = []
        if profil.aile_durumu and profil.aile_durumu != 'normal':
            flag.append(f"aile durumu: {profil.aile_durumu_str}")
        if profil.ekonomik_durum == 'dusuk':
            flag.append('ekonomik durum: dusuk')
        if flag:
            satirlar.append("Profil notu: " + ', '.join(flag))

    satirlar.append("--- (Bu metin otomatik uretildi; gerekli yerleri duzenleyin) ---")
    return "\n".join(satirlar)
