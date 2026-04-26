"""Deneme sinavi kategorileri ve ogrenci eslestirmesi.

Kategori = sinav tiplerinin ust seviye gruplandirmasi.
- 'yks': TYT, AYT-SAY/SOZ/EA/DIL → 9-12. sinif, TYT/AYT/Mezun
- 'lgs': LGS → 6-7-8. sinif
- 'msu': MSU askeri → 12. sinif/Mezun
- 'ozel': serbest

Ogrenci.sinif text alaninda 'i/i' farklari ('Sinif' vs 'Sınıf'), bosluklar,
TYT/AYT gibi dershane-spesifik etiketler bulunabildigi icin esneklikle
parse ediyoruz.
"""
import re

KATEGORILER = {
    'yks':  {'kod': 'yks',  'ad': 'YKS',  'badge': 'primary',  'aciklama': '9-12. sinif, TYT, AYT, Mezun'},
    'lgs':  {'kod': 'lgs',  'ad': 'LGS',  'badge': 'success',  'aciklama': '6-7-8. sinif'},
    'msu':  {'kod': 'msu',  'ad': 'MSU',  'badge': 'warning',  'aciklama': 'Askeri ogrenci alimi'},
    'ozel': {'kod': 'ozel', 'ad': 'Ozel', 'badge': 'secondary', 'aciklama': 'Serbest / kurum ici'},
}


# Sinav tipi -> kategori
TIP_KATEGORI_HARITA = {
    'tyt':     'yks',
    'ayt_say': 'yks',
    'ayt_soz': 'yks',
    'ayt_ea':  'yks',
    'ayt_dil': 'yks',
    'lgs':     'lgs',
    'msu':     'msu',
    'ozel':    'ozel',
}


def sinav_tipi_kategorisi(sinav_tipi):
    """'tyt' -> 'yks', 'lgs' -> 'lgs', vs."""
    return TIP_KATEGORI_HARITA.get(sinav_tipi, 'ozel')


def kategori_bilgi(kod):
    """{'kod','ad','badge','aciklama'} sozlugu dondur."""
    return KATEGORILER.get(kod, KATEGORILER['ozel'])


# Ogrenci sinif metni -> kategori
# Sinif metni dershanede serbestce girilebildigi icin esnek karsilastirma.
_LGS_PATTERNS = [
    re.compile(r'^\s*[6-8]\s*[\.\-/]?\s*s[ıi]n+[ıi]f', re.IGNORECASE),  # "8. Sınıf", "8 Sinif"
    re.compile(r'^\s*lgs\b', re.IGNORECASE),
    re.compile(r'\b8inci\b', re.IGNORECASE),
]
_YKS_PATTERNS = [
    re.compile(r'^\s*(9|10|11|12)\s*[\.\-/]?\s*s[ıi]n+[ıi]f', re.IGNORECASE),
    re.compile(r'^\s*tyt\b', re.IGNORECASE),
    re.compile(r'^\s*ayt(\b|_)', re.IGNORECASE),
    re.compile(r'^\s*ydt\b', re.IGNORECASE),
    re.compile(r'^\s*mezun\b', re.IGNORECASE),
    re.compile(r'^\s*yks\b', re.IGNORECASE),
]


def ogrenci_kategorisi(ogrenci):
    """Ogrencinin 'sinif' metnine gore kategori dondur ('yks' / 'lgs' / None).

    Kategorisi belirsiz ogrenciler icin None doner; bu durumda filtre
    'gostersinmi' kararini cagrana birakir (genelde dahil etmek dogru).
    """
    if not ogrenci:
        return None
    # Onceligi aktif kayit-sube-sinif zincirinden al, yoksa legacy ogrenci.sinif'i kullan
    try:
        sinif_metni = ogrenci.aktif_sinif_sube
    except Exception:
        sinif_metni = None
    if not sinif_metni:
        sinif_metni = (ogrenci.sinif or '').strip()
    if not sinif_metni:
        return None

    for p in _LGS_PATTERNS:
        if p.search(sinif_metni):
            return 'lgs'
    for p in _YKS_PATTERNS:
        if p.search(sinif_metni):
            return 'yks'
    return None


def ogrenci_uygun_mu(ogrenci, kategori, kategorisiz_dahil=True):
    """Ogrenci verilen kategoriye uygun mu? kategorisiz_dahil=True ise
    kategorisi belirsiz ogrenciler dahil edilir (filtre cok dar olmasin)."""
    if kategori in (None, 'ozel'):
        return True  # Ozel/MSU vs. icin filtreleme yapma
    og_kat = ogrenci_kategorisi(ogrenci)
    if og_kat is None:
        return kategorisiz_dahil
    return og_kat == kategori
