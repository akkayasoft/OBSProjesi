"""Deneme sinavi puan hesaplama.

Formuller 'yaklasik' — ÖSYM/MEB gercek formuleri std sapma iceren karmasik
hesaplamalar; dershane denemeleri icin genel kabul görmüş katsayi yontemi
kullanildi. Her DenemeDersi kendi 'katsayi' degeriyle gelir; 'alan' alani
AYT'de puan turleri icin kullanilir.

Tum fonksiyonlar bir DenemeKatilim veya liste-of-DersSonucu uzerinde calisir.
"""

SABIT_TABAN = 100.0  # YKS/LGS puanlarinin sabit taban degeri


def hesapla_net(dogru, yanlis):
    """Standart Turkiye formulu: net = dogru - yanlis/4."""
    d = dogru or 0
    y = yanlis or 0
    return round(d - (y / 4.0), 2)


def katilim_toplam_neti(katilim):
    """DenemeKatilim'in tum ders sonuclarindaki neti topla."""
    sonuclar = katilim.ders_sonuclari.all()
    return round(sum((s.net or 0) for s in sonuclar), 2)


def _puan_alan_filtreli(katilim, hedef_alanlar, alt_kirilim_dis=None):
    """Belirli alanlardaki derslerin net*katsayi toplamini doner.

    Eger hedef alan filtresine giren ders yoksa (0 ders eslesti), None doner;
    cagiran fonksiyon fallback uygulayabilir.

    hedef_alanlar: tek string ya da set/list.
    alt_kirilim_dis: bu ders_kodu set'inde olanlari haric tutar.
    """
    if isinstance(hedef_alanlar, str):
        hedef_alanlar = {hedef_alanlar}
    else:
        hedef_alanlar = set(hedef_alanlar)
    alt_kirilim_dis = alt_kirilim_dis or set()

    eslesen = 0
    katki = 0.0
    for sonuc in katilim.ders_sonuclari.all():
        ders = sonuc.ders
        if not ders or ders.alan not in hedef_alanlar:
            continue
        if ders.ders_kodu in alt_kirilim_dis:
            continue
        eslesen += 1
        kat = ders.katsayi or 0
        katki += (sonuc.net or 0) * kat
    if eslesen == 0:
        return None
    return katki


def _puan_tum_dersler(katilim):
    """Sinav tipinden bagimsiz, tum derslerin net*katsayi toplami.

    Fallback amaciyla: sinav tipi ile ders.alan uyumsuz oldugunda
    (ornek: tipi 'ayt_say' ama dersler 'tyt') yine de manali bir puan
    uretmek icin kullanilir.
    """
    katki = 0.0
    for sonuc in katilim.ders_sonuclari.all():
        ders = sonuc.ders
        if not ders:
            continue
        kat = ders.katsayi or 0
        katki += (sonuc.net or 0) * kat
    return katki


def hesapla_tyt_puani(katilim, alt_kirilimsiz=True):
    """TYT yaklasik puani: 100 + sum(net × katsayi).

    Once 'tyt' alanli dersleri kullanir; alt_kirilimsiz=True ile alt-kirilimi
    haric tutar. Eger 'tyt' alanli ders bulunamazsa (yanlis konfigurasyon),
    tum dersler uzerinden katsayili toplam alinir.
    """
    ALT_KIRILIM = {'tarih', 'cografya', 'felsefe', 'din',
                   'fizik', 'kimya', 'biyoloji'} if alt_kirilimsiz else set()
    katki = _puan_alan_filtreli(katilim, 'tyt', alt_kirilim_dis=ALT_KIRILIM)
    if katki is None:
        # Fallback: tum dersleri kullan
        katki = _puan_tum_dersler(katilim)
    return round(SABIT_TABAN + katki, 2)


def hesapla_ayt_puani(katilim, hedef_alan):
    """AYT icin SAY/SOZ/EA/DIL puani.

    hedef_alan: 'say' | 'soz' | 'ea' | 'dil'
    Formul: 100 + sum(AYT_ders_net × katsayi)

    Eger hedef_alan'a uyan ders yoksa (yanlis konfigurasyon), tum
    dersler uzerinden katsayili toplam alinir (fallback).
    """
    katki = _puan_alan_filtreli(katilim, hedef_alan)
    if katki is None:
        katki = _puan_tum_dersler(katilim)
    return round(SABIT_TABAN + katki, 2)


def hesapla_lgs_puani(katilim):
    """LGS yaklasik puani: 100 + sum(net × katsayi).

    Turkce/Matematik/Fen (4 katsayili) agirlikli, Inkilap/Din/Ing (1 kat)
    dusuk agirlikli. OBP bu hesaba katilmiyor (opsiyonel olarak kullanici
    girerse asagidaki hesapla_lgs_puani_with_obp kullanilabilir).
    """
    toplam = SABIT_TABAN
    for sonuc in katilim.ders_sonuclari.all():
        ders = sonuc.ders
        if not ders:
            continue
        kat = ders.katsayi or 0
        toplam += (sonuc.net or 0) * kat
    return round(toplam, 2)


def hesapla_lgs_puani_with_obp(katilim):
    """LGS + OBP (Okul Basari Puani) katkisi.

    MEB formulu: yerlestirme_puani = 0.7 × sinav_puani + 0.3 × OBP
    (OBP 100-500 aralikli bir deger olarak tutuluyor kabul ediliyor)
    """
    sinav_puani = hesapla_lgs_puani(katilim)
    obp = katilim.obp
    if obp is None:
        return sinav_puani
    return round(0.7 * sinav_puani + 0.3 * obp, 2)


def hesapla_puan(katilim):
    """Sinav tipine gore uygun puan fonksiyonu; katilim.toplam_puan'a yazilir."""
    sinav = katilim.sinav
    if not sinav:
        return None
    tip = sinav.sinav_tipi
    if tip == 'tyt':
        return hesapla_tyt_puani(katilim)
    if tip == 'ayt_say':
        return hesapla_ayt_puani(katilim, 'say')
    if tip == 'ayt_soz':
        return hesapla_ayt_puani(katilim, 'soz')
    if tip == 'ayt_ea':
        return hesapla_ayt_puani(katilim, 'ea')
    if tip == 'ayt_dil':
        return hesapla_ayt_puani(katilim, 'dil')
    if tip == 'lgs':
        if katilim.obp is not None:
            return hesapla_lgs_puani_with_obp(katilim)
        return hesapla_lgs_puani(katilim)
    if tip == 'msu':
        # MSU TYT'ye benzer hesap
        return hesapla_tyt_puani(katilim)
    # 'ozel' ya da bilinmeyen: sade toplam net * 2 + 100
    return round(SABIT_TABAN + (katilim.toplam_net or 0) * 2, 2)


def guncelle_katilim_toplamlari(katilim):
    """Bir katilim icin tum ders sonuclarini hesaplayip toplamlari gunceller.

    1) Her DersSonucu.net yeniden hesapla
    2) Katilim toplam dogru/yanlis/bos/net guncelle
    3) Sinav tipine gore yaklasik puani hesaplayip toplam_puan'a yaz
    """
    sonuclar = katilim.ders_sonuclari.all()
    for s in sonuclar:
        s.hesapla_net()
    katilim.hesapla_toplamlari()
    katilim.toplam_puan = hesapla_puan(katilim)
