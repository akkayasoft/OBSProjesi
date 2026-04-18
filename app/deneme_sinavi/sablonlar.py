"""Resmi sinav formatlarina gore ders blogu sablonlari.

Her sablon: soru sayilari, sure, puan hesabinda kullanilacak katsayilar.
Katsayilar "yaklasik" — ÖSYM/MEB gerçek formüllerine birebir uymaz ama
dershane denemeleri icin kullanilan genel kabul görmüş değerlerdir.

Yeni sinav olustururken create_from_template() ile kullanilir.
"""

# Sinav tipine gore ders blogu sablonu.
# Her ders: (kod, ad, soru_sayisi, katsayi, alan)
SABLONLAR = {
    'tyt': {
        'ad': 'YKS - TYT',
        'sure_dakika': 135,
        'dersler': [
            ('turkce',       'Turkce',              40, 3.3, 'tyt'),
            ('sosyal',       'Sosyal Bilimler',     20, 3.4, 'tyt'),
            ('tarih',        'Tarih',                5, 3.4, 'tyt'),   # opsiyonel alt kirilim
            ('cografya',     'Cografya',             5, 3.4, 'tyt'),
            ('felsefe',      'Felsefe',              5, 3.4, 'tyt'),
            ('din',          'Din Kulturu',          5, 3.4, 'tyt'),
            ('matematik',    'Temel Matematik',     40, 3.3, 'tyt'),
            ('fen',          'Fen Bilimleri',       20, 3.4, 'tyt'),
            ('fizik',        'Fizik',                7, 3.4, 'tyt'),
            ('kimya',        'Kimya',                7, 3.4, 'tyt'),
            ('biyoloji',     'Biyoloji',             6, 3.4, 'tyt'),
        ],
        # Varsayilan "hizli" secim: birlesik bloklar (alt kirilim olmadan)
        'varsayilan': ['turkce', 'sosyal', 'matematik', 'fen'],
    },

    'ayt_say': {
        'ad': 'YKS - AYT Sayisal',
        'sure_dakika': 180,
        'dersler': [
            ('matematik_ayt', 'Matematik (AYT)',    40, 3.0, 'say'),
            ('fizik_ayt',     'Fizik',              14, 2.85, 'say'),
            ('kimya_ayt',     'Kimya',              13, 2.85, 'say'),
            ('biyoloji_ayt',  'Biyoloji',           13, 3.0, 'say'),
        ],
        'varsayilan': ['matematik_ayt', 'fizik_ayt', 'kimya_ayt', 'biyoloji_ayt'],
    },

    'ayt_soz': {
        'ad': 'YKS - AYT Sozel',
        'sure_dakika': 180,
        'dersler': [
            ('edebiyat',      'Turk Dili ve Edebiyati', 24, 3.0, 'soz'),
            ('tarih1',        'Tarih-1',                10, 2.85, 'soz'),
            ('cografya1',     'Cografya-1',              6, 2.85, 'soz'),
            ('tarih2',        'Tarih-2',                11, 2.14, 'soz'),
            ('cografya2',     'Cografya-2',             11, 2.14, 'soz'),
            ('felsefe_ayt',   'Felsefe Grubu',          12, 3.0, 'soz'),
            ('din_ayt',       'Din Kulturu',             6, 1.07, 'soz'),
        ],
        'varsayilan': ['edebiyat', 'tarih1', 'cografya1', 'tarih2',
                       'cografya2', 'felsefe_ayt', 'din_ayt'],
    },

    'ayt_ea': {
        'ad': 'YKS - AYT Esit Agirlik',
        'sure_dakika': 180,
        'dersler': [
            ('matematik_ayt', 'Matematik (AYT)',         40, 3.0, 'ea'),
            ('edebiyat',      'Turk Dili ve Edebiyati',  24, 3.0, 'ea'),
            ('tarih1',        'Tarih-1',                 10, 2.85, 'ea'),
            ('cografya1',     'Cografya-1',               6, 2.85, 'ea'),
        ],
        'varsayilan': ['matematik_ayt', 'edebiyat', 'tarih1', 'cografya1'],
    },

    'ayt_dil': {
        'ad': 'YKS - YDT (Yabanci Dil)',
        'sure_dakika': 120,
        'dersler': [
            ('yabanci_dil',   'Yabanci Dil',            80, 3.0, 'dil'),
        ],
        'varsayilan': ['yabanci_dil'],
    },

    'lgs': {
        'ad': 'LGS',
        'sure_dakika': 155,
        'dersler': [
            ('turkce',        'Turkce',                  20, 4.0, 'sozel'),
            ('inkilap',       'T.C. Inkilap Tarihi',     10, 1.0, 'sozel'),
            ('din',           'Din Kulturu',             10, 1.0, 'sozel'),
            ('ingilizce',     'Yabanci Dil (Ingilizce)', 10, 1.0, 'sozel'),
            ('matematik',     'Matematik',               20, 4.0, 'sayisal'),
            ('fen',           'Fen Bilimleri',           20, 4.0, 'sayisal'),
        ],
        'varsayilan': ['turkce', 'inkilap', 'din', 'ingilizce', 'matematik', 'fen'],
    },

    'msu': {
        'ad': 'MSU (Askeri Ogrenci Alim)',
        'sure_dakika': 135,
        'dersler': [
            ('turkce',        'Turkce',                  40, 3.3, 'msu'),
            ('sosyal',        'Sosyal Bilimler',         20, 3.4, 'msu'),
            ('matematik',     'Temel Matematik',         40, 3.3, 'msu'),
            ('fen',           'Fen Bilimleri',           20, 3.4, 'msu'),
        ],
        'varsayilan': ['turkce', 'sosyal', 'matematik', 'fen'],
    },

    'ozel': {
        'ad': 'Ozel / Serbest Sinav',
        'sure_dakika': 90,
        'dersler': [],
        'varsayilan': [],
    },
}


def get_sablon(sinav_tipi):
    """Tipe gore sablon sozlugu dondur; bilinmezse 'ozel' verir."""
    return SABLONLAR.get(sinav_tipi, SABLONLAR['ozel'])


def varsayilan_dersler(sinav_tipi):
    """Tipi olan sinavin 'birlesik' (alt kirilimsiz) varsayilan derslerini dondur.

    Her item: {kod, ad, soru_sayisi, katsayi, alan, sira}
    """
    sablon = get_sablon(sinav_tipi)
    secim = set(sablon.get('varsayilan', []))
    dersler = []
    sira = 1
    for kod, ad, soru, kat, alan in sablon.get('dersler', []):
        if not secim or kod in secim:
            dersler.append({
                'ders_kodu': kod,
                'ders_adi': ad,
                'soru_sayisi': soru,
                'katsayi': kat,
                'alan': alan,
                'sira': sira,
            })
            sira += 1
    return dersler


def tum_dersler(sinav_tipi):
    """Sablondaki tum dersleri dondur (alt kirilim dahil — ozel kullanim)."""
    sablon = get_sablon(sinav_tipi)
    dersler = []
    for i, (kod, ad, soru, kat, alan) in enumerate(sablon.get('dersler', []), 1):
        dersler.append({
            'ders_kodu': kod,
            'ders_adi': ad,
            'soru_sayisi': soru,
            'katsayi': kat,
            'alan': alan,
            'sira': i,
        })
    return dersler
