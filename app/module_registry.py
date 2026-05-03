"""Modul kayit defteri.

- URL prefix -> modul_key eslemesi (decorator ve izin kontrolu icin)
- Onceden tanimli modul paketleri (yonetici icin preset'ler)

Yeni bir modul eklediginde hem buraya hem RolModulIzin.MODULLER'e ekle.
"""

# URL prefix -> modul_key
# NOT: role_required ve inject_menu bu listeyi kullanir.
# Uzun prefix'lerin once gelmesi icin sorted erisim saglanir (asagida helper var).
MODUL_URL_PREFIX = {
    'muhasebe': '/muhasebe',
    'kayit': '/kayit',
    'devamsizlik': '/devamsizlik',
    'personel': '/personel',
    'ders_dagitimi': '/ders-dagitimi',
    'not_defteri': '/not-defteri',
    'duyurular': '/duyurular',
    'rehberlik': '/rehberlik',
    'saglik': '/saglik',
    'iletisim': '/iletisim',
    'online_sinav': '/online-sinav',
    'kulupler': '/kulupler',
    'kullanici': '/kullanici',
    'kurum': '/kurum',
    'ayarlar': '/ayarlar',
    'ogretmen_portal': '/ogretmen',
    'ogrenci_portal': '/portal',
    'bildirim': '/bildirim',
    'odev_takip': '/odev',
    'davranis': '/davranis',
    'karne': '/karne',
    'etut': '/etut',
    'sinav_oturum': '/sinav-oturum',
    'ortak_sinav': '/ortak-sinav',
    'deneme_sinavi': '/deneme-sinavi',
    'anket': '/anket',
    'servis': '/servis',
    'kantin': '/kantin',
    'kutuphane': '/kutuphane',
    'envanter': '/envanter',
    'yurt': '/yurt',
    'raporlama': '/raporlama',
    'denetim': '/denetim',
    'belge': '/belge',
    'ders_programi': '/ders-programi',
    # Surucu kursu URL'leri
    'surucu_kursiyer':    '/surucu-kursu/kursiyer',
    'surucu_sinav_harc':  '/surucu-kursu/sinav-harc',
    'surucu_yonlendirme': '/surucu-kursu/yonlendirmeler',
    'surucu_rapor':       '/surucu-kursu/rapor',
}


def url_to_modul_key(path: str):
    """Verilen request path'inin hangi module ait oldugunu dondur.
    Hic eslesme yoksa None. En uzun prefix once gelir ki /ders-dagitimi'ni
    /ders-programi'ndan once yakalasin.
    """
    if not path:
        return None
    # Uzun olandan once kontrol et
    sorted_items = sorted(MODUL_URL_PREFIX.items(), key=lambda x: len(x[1]), reverse=True)
    for modul_key, prefix in sorted_items:
        if path == prefix or path.startswith(prefix + '/'):
            return modul_key
    return None


# ---------------------------------------------------------------------------
# Onceden tanimli paketler (admin yonetici olustururken hazir secebilir)
# ---------------------------------------------------------------------------
# NOT: Admin icin ozel olan moduller BU listelere dahil EDILMEZ:
#   - kullanici (sistem kullanici yonetimi, yonetici ve admin hesaplarini kapsar)
#   - denetim   (audit log, sadece admin)
#   - ayarlar   (sistem ayarlari, sadece admin)
# Yonetici yine de 'kurum' ve is modullerini gorebilir.

PRESETLER = {
    'baslangic': {
        'ad': 'Baslangic',
        'aciklama': 'Temel modul seti: ogrenci kayit, muhasebe, devamsizlik, duyuru, iletisim.',
        'moduller': [
            'kayit',
            'muhasebe',
            'devamsizlik',
            'duyurular',
            'iletisim',
            'bildirim',
            'kurum',
        ],
    },
    'standart': {
        'ad': 'Standart',
        'aciklama': 'Akademik ve operasyonel modullerle genis paket.',
        'moduller': [
            'kayit',
            'muhasebe',
            'devamsizlik',
            'personel',
            'kullanici',
            'ders_dagitimi',
            'not_defteri',
            'karne',
            'etut',
            'sinav_oturum',
            'online_sinav',
            'duyurular',
            'iletisim',
            'bildirim',
            'kurum',
            'ogretmen_portal',
            'ogrenci_portal',
            'ders_programi',
            'odev_takip',
            'davranis',
            'raporlama',
            'ayarlar',
        ],
    },
    'kurumsal': {
        'ad': 'Kurumsal',
        'aciklama': 'Tum is modulleri + kullanici yonetimi (sistem yoneticileri haric).',
        'moduller': [
            'muhasebe',
            'kayit',
            'devamsizlik',
            'personel',
            'kullanici',
            'ders_dagitimi',
            'not_defteri',
            'odev_takip',
            'davranis',
            'karne',
            'etut',
            'sinav_oturum',
            'duyurular',
            'rehberlik',
            'saglik',
            'iletisim',
            'online_sinav',
            'kulupler',
            'ortak_sinav',
            'deneme_sinavi',
            'anket',
            'servis',
            'kantin',
            'kutuphane',
            'envanter',
            'yurt',
            'ders_programi',
            'raporlama',
            'belge',
            'bildirim',
            'kurum',
            'ogretmen_portal',
            'ogrenci_portal',
        ],
    },
}


def preset_moduller(preset_key: str):
    """Verilen preset anahtarina ait modul listesini dondur. Yoksa []."""
    preset = PRESETLER.get(preset_key)
    return list(preset['moduller']) if preset else []


# ---------------------------------------------------------------------------
# Modul renk kategorileri
# ---------------------------------------------------------------------------
# Her kategori icin: css class suffix, hex renk (sidebar accent + sayfa baslik)

MODUL_RENKLERI = {
    # Akademik — Mavi
    'not_defteri':    'akademik',
    'karne':          'akademik',
    'ders_dagitimi':  'akademik',
    'ders_programi':  'akademik',
    'etut':           'akademik',
    'sinav_oturum':   'akademik',
    'online_sinav':   'akademik',
    'ortak_sinav':    'akademik',
    'deneme_sinavi':  'akademik',
    'odev_takip':     'akademik',
    'davranis':       'akademik',
    'ogretmen_portal':'akademik',

    # Kayit & Ogrenci — Yesil
    'kayit':          'kayit',
    'ogrenci_portal': 'kayit',
    'devamsizlik':    'kayit',

    # Finans — Turuncu
    'muhasebe':       'finans',

    # Personel & Iletisim — Mor
    'personel':       'iletisim',
    'iletisim':       'iletisim',
    'duyurular':      'iletisim',
    'bildirim':       'iletisim',

    # Kurum & Yonetim — Slate
    'kurum':          'yonetim',
    'kullanici':      'yonetim',
    'ayarlar':        'yonetim',
    'denetim':        'yonetim',
    'raporlama':      'yonetim',
    'belge':          'yonetim',

    # Sosyal & Destek — Cyan
    'kulupler':       'sosyal',
    'anket':          'sosyal',
    'rehberlik':      'sosyal',
    'saglik':         'sosyal',

    # Lojistik — Rose
    'servis':         'lojistik',
    'kantin':         'lojistik',
    'kutuphane':      'lojistik',
    'envanter':       'lojistik',
    'yurt':           'lojistik',
}

KATEGORI_RENKLERI = {
    'akademik':  {'hex': '#3b82f6', 'label': 'Akademik'},
    'kayit':     {'hex': '#10b981', 'label': 'Kayit & Ogrenci'},
    'finans':    {'hex': '#f59e0b', 'label': 'Finans'},
    'iletisim':  {'hex': '#8b5cf6', 'label': 'Personel & Iletisim'},
    'yonetim':   {'hex': '#64748b', 'label': 'Kurum & Yonetim'},
    'sosyal':    {'hex': '#06b6d4', 'label': 'Sosyal & Destek'},
    'lojistik':  {'hex': '#f43f5e', 'label': 'Lojistik'},
}


def modul_renk_kategorisi(modul_key: str) -> str:
    """Modul key'ine gore renk kategorisini dondur."""
    return MODUL_RENKLERI.get(modul_key, 'yonetim')


def modul_renk_hex(modul_key: str) -> str:
    """Modul key'ine gore hex renk kodunu dondur."""
    kat = modul_renk_kategorisi(modul_key)
    return KATEGORI_RENKLERI.get(kat, {}).get('hex', '#64748b')
