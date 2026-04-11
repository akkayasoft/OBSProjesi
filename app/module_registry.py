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
        ],
    },
    'kurumsal': {
        'ad': 'Kurumsal',
        'aciklama': 'Sistem modulleri (kullanici, denetim, ayarlar) haric tum is modulleri.',
        'moduller': [
            'muhasebe',
            'kayit',
            'devamsizlik',
            'personel',
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
