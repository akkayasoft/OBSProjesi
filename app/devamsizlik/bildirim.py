"""Devamsizlik bildirim yardimcilari.

Yoklama kaydedildiginde 'devamsiz' isaretlenen ogrencilerin kendisine
ve velilerine bildirim olusturur. Spam'i onlemek icin sadece YENI
isaretlenen (onceki durumu devamsiz OLMAYAN) kayitlar icin bildirim
atilir.

Sistem ayari 'otomatik_bildirim' false ise bildirim atilmaz.
"""
from collections import defaultdict
from typing import Iterable

from app.extensions import db
from app.models.bildirim import Bildirim
from app.models.devamsizlik import Devamsizlik


def _bildirim_aktif_mi() -> bool:
    """SistemAyar'dan otomatik bildirim acik mi kontrolu."""
    try:
        from app.models.ayarlar import SistemAyar
        a = SistemAyar.query.filter_by(anahtar='otomatik_bildirim').first()
        if a is None:
            return True  # ayar yoksa default acik
        return str(a.deger).strip().lower() in ('true', '1', 'yes', 'evet', 'on')
    except Exception:
        return True


def _veli_user_idleri(ogrenci_id: int) -> list[int]:
    """Bir ogrencinin tum velilerinin user_id'lerini dondur (None'lar haric)."""
    try:
        from app.models.kayit import VeliBilgisi
        veliler = VeliBilgisi.query.filter_by(ogrenci_id=ogrenci_id).all()
        return [v.user_id for v in veliler if v.user_id]
    except Exception:
        return []


def devamsizlik_bildirimleri_gonder(yeni_kayitlar: Iterable[Devamsizlik]) -> int:
    """Verilen Devamsizlik kayitlari icin ogrenci+veli bildirimleri olustur.

    Sadece durum='devamsiz' olanlar icin bildirim atilir; gec/izinli/
    raporlu icin atlanir. Ayni ogrencinin birden fazla ders saati ayni
    gun devamsiz ise konsolide tek bildirim olusur (spam azaltma).

    db.session.add ile bildirim ekler ama COMMIT YAPMAZ — cagiranin
    sorumlulugundadir.

    Returns: olusturulan bildirim sayisi (kullanici basina toplam).
    """
    if not _bildirim_aktif_mi():
        return 0

    devamsizlar = [k for k in yeni_kayitlar if k and k.durum == 'devamsiz']
    if not devamsizlar:
        return 0

    # Ogrenci_id -> {tarih, ders_saatleri, ogrenci_obj}
    grup: dict[int, dict] = defaultdict(
        lambda: {'tarih': None, 'ders_saatleri': set(), 'ogrenci': None}
    )
    for k in devamsizlar:
        g = grup[k.ogrenci_id]
        g['tarih'] = k.tarih
        g['ders_saatleri'].add(k.ders_saati)
        if g['ogrenci'] is None:
            g['ogrenci'] = k.ogrenci

    olusturulan = 0
    for ogrenci_id, g in grup.items():
        ogrenci = g['ogrenci']
        if ogrenci is None:
            continue

        ds_sira = sorted(g['ders_saatleri'])
        ds_str = ', '.join(str(d) for d in ds_sira)
        tarih_str = g['tarih'].strftime('%d.%m.%Y') if g['tarih'] else ''
        adet_label = (f'{len(ds_sira)} ders saati ({ds_str}.)'
                      if len(ds_sira) > 1 else f'{ds_str}. ders')

        # Hedefler: ogrencinin kendisi + tum velileri (user_id'li olanlar)
        hedefler: list[tuple[int, str, str]] = []  # (kullanici_id, baslik, link)
        if ogrenci.user_id:
            hedefler.append((
                ogrenci.user_id,
                'Devamsızlık Bildirimi',
                '/portal/devamsizlik/',
            ))
        for veli_uid in _veli_user_idleri(ogrenci_id):
            hedefler.append((
                veli_uid,
                f'{ogrenci.tam_ad} — Devamsızlık Bildirimi',
                '/portal/veli/',
            ))

        if not hedefler:
            continue

        # Mesaj govdesi (hedefe gore birazcik farklilastir)
        for kid, baslik, link in hedefler:
            if 'Veli' in link:
                mesaj = (f'{ogrenci.tam_ad} {tarih_str} tarihinde '
                         f'{adet_label} devamsız olarak işaretlendi.')
            else:
                mesaj = (f'{tarih_str} tarihinde {adet_label} '
                         f'devamsız olarak işaretlendiniz.')
            db.session.add(Bildirim(
                kullanici_id=kid,
                baslik=baslik,
                mesaj=mesaj,
                tur='uyari',
                kategori='devamsizlik',
                link=link,
            ))
            olusturulan += 1

    return olusturulan


def yeni_devamsiz_kayitlari_filtrele(
    yeni_kayitlar: list[Devamsizlik],
    onceki_kayitlar: dict,
) -> list[Devamsizlik]:
    """Spam'i onle: sadece onceden 'devamsiz' OLMAYAN ogrenciler icin
    bildirim hak eden kayitlari filtrele.

    onceki_kayitlar: {ogrenci_id: Devamsizlik} formatinda — yoklama
    kaydedilmeden once mevcut olan kayitlar.
    """
    sonuc = []
    for k in yeni_kayitlar:
        if k.durum != 'devamsiz':
            continue
        eski = onceki_kayitlar.get(k.ogrenci_id)
        # Eger ayni ders saatinde zaten devamsiz idi, atla
        if eski is not None and eski.durum == 'devamsiz' \
                and eski.ders_saati == k.ders_saati:
            continue
        sonuc.append(k)
    return sonuc
