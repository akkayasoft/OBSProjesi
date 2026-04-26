"""Ogrenci risk skoru: erken uyari sistemi.

Bu modul ogrencilerin akademik + davranissal + devam sinyallerini birlestirip
0-100 araliginda kompozit bir risk skoru uretir. Amac, rehber ogretmenin
kalabalik bir okulda 'gormediği' ogrenciyi haftalik olarak listeye dusurmek.

Sinyaller:
    1. Devamsizlik   (son 30 gun, durum='devamsiz')   -> 0..35
    2. Deneme trend  (son 3 katilim)                  -> 0..35
    3. Davranis      (son 14 gun, tur='olumsuz')      -> 0..25
    4. Profil bayrak (rehberlik profilinden)          -> 0..5

Toplam 0..100, esikler:
    0-29   'dusuk'   (yesil)
    30-54  'orta'    (sari)
    55-100 'yuksek'  (kirmizi)

Cikis sozlugu (ogrenci_risk_skoru):
    {
        'ogrenci': Ogrenci,
        'skor': int,                 # 0..100
        'seviye': 'dusuk'|'orta'|'yuksek',
        'badge': 'success'|'warning'|'danger',
        'sebepler': [str, ...],      # badge'lenmek uzere kisa metinler
        'detay': {
            'devamsizlik': {'gun_sayisi': int, 'puan': int},
            'deneme':      {'trend': str, 'puan': int, 'son_yuzdelik': int|None},
            'davranis':    {'olumsuz_sayi': int, 'puan': int},
            'profil':      {'puan': int, 'aciklama': str|None},
        },
    }

Hicbir sinyal yoksa skor 0 dondurulur.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import func

from app.extensions import db
from app.models.deneme_sinavi import DenemeKatilim, DenemeSinavi
from app.models.devamsizlik import Devamsizlik
from app.models.muhasebe import Ogrenci
from app.models.rehberlik import DavranisKaydi, OgrenciProfil


# --- Sabitler -------------------------------------------------------------

DEVAMSIZLIK_PENCERE_GUN = 30
DAVRANIS_PENCERE_GUN = 14
DENEME_PENCERE = 3

SEVIYE_ESIK = {
    'dusuk': 30,    # < 30 -> dusuk
    'orta': 55,     # < 55 -> orta, >= 55 yuksek
}

SEVIYE_BADGE = {
    'dusuk': 'success',
    'orta': 'warning',
    'yuksek': 'danger',
}


# --- Sinyal hesaplari -----------------------------------------------------

def _devamsizlik_skoru(ogrenci_id: int, bugun: date) -> tuple[int, int, int]:
    """Son DEVAMSIZLIK_PENCERE_GUN gun icindeki devamsiz ders saati sayisina gore puan.

    Donus: (puan, devamsiz_ders_saati_sayisi, devamsiz_gun_sayisi)
    """
    baslangic = bugun - timedelta(days=DEVAMSIZLIK_PENCERE_GUN)
    saat_sayisi = (Devamsizlik.query
                   .filter(Devamsizlik.ogrenci_id == ogrenci_id,
                           Devamsizlik.tarih >= baslangic,
                           Devamsizlik.durum == 'devamsiz')
                   .count())
    gun_sayisi = (db.session.query(func.count(func.distinct(Devamsizlik.tarih)))
                  .filter(Devamsizlik.ogrenci_id == ogrenci_id,
                          Devamsizlik.tarih >= baslangic,
                          Devamsizlik.durum == 'devamsiz')
                  .scalar()) or 0

    # Esikler tam gun bazli (saat degil): 1 tam gun ortalama 6-8 ders saatidir.
    if gun_sayisi == 0:
        puan = 0
    elif gun_sayisi == 1:
        puan = 5
    elif gun_sayisi <= 3:
        puan = 12
    elif gun_sayisi <= 6:
        puan = 22
    else:
        puan = 35

    return puan, saat_sayisi, gun_sayisi


def _deneme_skoru(ogrenci_id: int) -> tuple[int, dict]:
    """Son DENEME_PENCERE deneme katiliminin trendine gore puan.

    Donus: (puan, detay)
    """
    katilimlar = (DenemeKatilim.query
                  .join(DenemeSinavi, DenemeKatilim.deneme_sinavi_id == DenemeSinavi.id)
                  .filter(DenemeKatilim.ogrenci_id == ogrenci_id,
                          DenemeKatilim.katildi == True,  # noqa: E712
                          DenemeKatilim.toplam_puan.isnot(None),
                          DenemeSinavi.durum.in_(('uygulandi', 'tamamlandi')))
                  .order_by(DenemeSinavi.tarih.desc())
                  .limit(DENEME_PENCERE)
                  .all())

    detay = {
        'katilim_sayisi': len(katilimlar),
        'trend': None,
        'son_yuzdelik': None,
        'puan': 0,
    }
    if not katilimlar:
        return 0, detay

    # Trend: en eski->en yeni puan farki
    puanlar = [k.toplam_puan for k in reversed(katilimlar) if k.toplam_puan is not None]
    if len(puanlar) >= 2:
        fark = puanlar[-1] - puanlar[0]
        if fark > 5:
            trend = 'yukseliyor'
        elif fark < -5:
            trend = 'dusuyor'
        else:
            trend = 'sabit'
        detay['trend'] = trend
        detay['trend_fark'] = round(fark, 2)
    else:
        detay['trend'] = 'yetersiz'

    puan = 0
    # Trend dusuyorsa puan ekle
    if detay.get('trend') == 'dusuyor':
        # Dusus 15 puandan fazlaysa daha siddetli
        if abs(detay.get('trend_fark', 0)) >= 15:
            puan += 25
        else:
            puan += 15

    # Son denemede yuzdelik dilim hesapla
    son = katilimlar[0]
    toplam = (DenemeKatilim.query
              .filter(DenemeKatilim.deneme_sinavi_id == son.deneme_sinavi_id,
                      DenemeKatilim.toplam_puan.isnot(None))
              .count())
    if toplam > 0 and son.toplam_puan is not None:
        ustte = (DenemeKatilim.query
                 .filter(DenemeKatilim.deneme_sinavi_id == son.deneme_sinavi_id,
                         DenemeKatilim.toplam_puan > son.toplam_puan)
                 .count())
        yuzdelik = max(1, min(100, int(((ustte + 1) / toplam) * 100)))
        detay['son_yuzdelik'] = yuzdelik
        # Alt %20: ek puan
        if yuzdelik >= 80:
            puan += 10

    puan = min(puan, 35)
    detay['puan'] = puan
    return puan, detay


def _davranis_skoru(ogrenci_id: int, bugun: date) -> tuple[int, int]:
    """Son DAVRANIS_PENCERE_GUN gun icindeki olumsuz davranis sayisina gore puan."""
    baslangic = bugun - timedelta(days=DAVRANIS_PENCERE_GUN)
    olumsuz = (DavranisKaydi.query
               .filter(DavranisKaydi.ogrenci_id == ogrenci_id,
                       DavranisKaydi.tarih >= baslangic,
                       DavranisKaydi.tur == 'olumsuz')
               .count())

    if olumsuz == 0:
        puan = 0
    elif olumsuz == 1:
        puan = 5
    elif olumsuz == 2:
        puan = 15
    else:
        puan = 25

    return puan, olumsuz


def _profil_skoru(ogrenci_id: int) -> tuple[int, str | None]:
    """Rehberlik profili icindeki risk faktorleri (modifier)."""
    profil = OgrenciProfil.query.filter_by(ogrenci_id=ogrenci_id).first()
    if not profil:
        return 0, None

    notlar = []
    puan = 0
    if profil.aile_durumu in ('bosanmis', 'vefat', 'tek_ebeveyn'):
        puan += 3
        notlar.append({
            'bosanmis': 'Aile durumu: Bosanmis',
            'vefat': 'Aile durumu: Vefat',
            'tek_ebeveyn': 'Aile durumu: Tek ebeveyn',
        }[profil.aile_durumu])
    if profil.ekonomik_durum == 'dusuk':
        puan += 2
        notlar.append('Ekonomik durum: Dusuk')

    aciklama = ' / '.join(notlar) if notlar else None
    return puan, aciklama


# --- Ana fonksiyon --------------------------------------------------------

def ogrenci_risk_skoru(ogrenci_id: int, bugun: date | None = None) -> dict[str, Any]:
    """Bir ogrenci icin kompozit risk skoru."""
    bugun = bugun or date.today()

    ogrenci = Ogrenci.query.get(ogrenci_id)
    if not ogrenci:
        return {
            'ogrenci': None,
            'skor': 0,
            'seviye': 'dusuk',
            'badge': 'success',
            'sebepler': [],
            'detay': {},
        }

    dev_puan, dev_saat, dev_gun = _devamsizlik_skoru(ogrenci_id, bugun)
    den_puan, den_detay = _deneme_skoru(ogrenci_id)
    dav_puan, dav_sayi = _davranis_skoru(ogrenci_id, bugun)
    pro_puan, pro_aciklama = _profil_skoru(ogrenci_id)

    skor = min(100, dev_puan + den_puan + dav_puan + pro_puan)

    if skor < SEVIYE_ESIK['dusuk']:
        seviye = 'dusuk'
    elif skor < SEVIYE_ESIK['orta']:
        seviye = 'orta'
    else:
        seviye = 'yuksek'

    sebepler: list[str] = []
    if dev_gun > 0:
        sebepler.append(f'{dev_gun} gun devamsizlik (30g)')
    if den_detay.get('trend') == 'dusuyor':
        fark = den_detay.get('trend_fark') or 0
        sebepler.append(f'Deneme dusus {fark:+.1f}p')
    if den_detay.get('son_yuzdelik') and den_detay['son_yuzdelik'] >= 80:
        sebepler.append(f'Dilim %{den_detay["son_yuzdelik"]}')
    if dav_sayi > 0:
        sebepler.append(f'{dav_sayi} olumsuz davranis (14g)')
    if pro_aciklama:
        sebepler.append(pro_aciklama)

    return {
        'ogrenci': ogrenci,
        'skor': skor,
        'seviye': seviye,
        'badge': SEVIYE_BADGE[seviye],
        'sebepler': sebepler,
        'detay': {
            'devamsizlik': {
                'gun_sayisi': dev_gun,
                'saat_sayisi': dev_saat,
                'puan': dev_puan,
            },
            'deneme': {**den_detay},
            'davranis': {
                'olumsuz_sayi': dav_sayi,
                'puan': dav_puan,
            },
            'profil': {
                'puan': pro_puan,
                'aciklama': pro_aciklama,
            },
        },
    }


def risk_snapshot_kaydet(ogrenci_id: int,
                          bugun: date | None = None,
                          force: bool = False) -> 'RiskSkoruGecmisi | None':
    """Bir ogrenci icin gunun risk skoru snapshot'ini DB'ye yazar.

    Ayni gunde mevcut bir snapshot varsa: force=True ise gunceller, degilse
    es gecer. ISO haftaya gore bir snapshot/hafta yeterli — varsayilan olarak
    haftada 1 kez calistirilmasi beklenir.

    Donus: olusturulan/guncellenen kayit, ya da None.
    """
    from app.models.rehberlik import RiskSkoruGecmisi  # circular import guard

    bugun = bugun or date.today()
    risk = ogrenci_risk_skoru(ogrenci_id, bugun=bugun)
    if not risk.get('ogrenci'):
        return None

    mevcut = (RiskSkoruGecmisi.query
              .filter_by(ogrenci_id=ogrenci_id, snapshot_tarih=bugun)
              .first())
    if mevcut and not force:
        return mevcut

    detay = risk.get('detay', {}) or {}
    sebepler_csv = ','.join(risk.get('sebepler', []) or [])

    if mevcut:
        mevcut.skor = risk['skor']
        mevcut.seviye = risk['seviye']
        mevcut.devamsizlik_gun = (detay.get('devamsizlik') or {}).get('gun_sayisi', 0)
        mevcut.olumsuz_davranis = (detay.get('davranis') or {}).get('olumsuz_sayi', 0)
        mevcut.deneme_trend = (detay.get('deneme') or {}).get('trend')
        mevcut.sebepler = sebepler_csv
        kayit = mevcut
    else:
        kayit = RiskSkoruGecmisi(
            ogrenci_id=ogrenci_id,
            snapshot_tarih=bugun,
            skor=risk['skor'],
            seviye=risk['seviye'],
            devamsizlik_gun=(detay.get('devamsizlik') or {}).get('gun_sayisi', 0),
            olumsuz_davranis=(detay.get('davranis') or {}).get('olumsuz_sayi', 0),
            deneme_trend=(detay.get('deneme') or {}).get('trend'),
            sebepler=sebepler_csv,
        )
        db.session.add(kayit)
    return kayit


def risk_snapshot_toplu(force: bool = False) -> dict:
    """Tum aktif ogrenciler icin gunun snapshot'ini olusturur.

    Donus: {'olusturulan': N, 'guncellenen': M, 'es_gecilen': K, 'toplam': T}
    """
    from app.models.rehberlik import RiskSkoruGecmisi

    bugun = date.today()
    aktifler = Ogrenci.query.filter_by(aktif=True).all()
    olusturulan = guncellenen = es_gecilen = 0
    for o in aktifler:
        mevcut = (RiskSkoruGecmisi.query
                  .filter_by(ogrenci_id=o.id, snapshot_tarih=bugun)
                  .first())
        if mevcut and not force:
            es_gecilen += 1
            continue
        kayit = risk_snapshot_kaydet(o.id, bugun=bugun, force=force)
        if kayit is None:
            continue
        if mevcut:
            guncellenen += 1
        else:
            olusturulan += 1

    db.session.commit()
    return {
        'olusturulan': olusturulan,
        'guncellenen': guncellenen,
        'es_gecilen': es_gecilen,
        'toplam': len(aktifler),
        'tarih': bugun,
    }


def risk_trend(ogrenci_id: int, hafta_sayisi: int = 12,
                bugune_kayit_garanti: bool = True) -> dict:
    """Bir ogrencinin son N haftadaki risk skoru trendini dondurur.

    Eger bugun icin snapshot yoksa ve `bugune_kayit_garanti=True` ise once
    snapshot kaydedilir, sonra trend hesaplanir. Bu sayede profile sayfasi
    her acildiginda guncel veri uretilir (cron beklenmesine gerek kalmaz).
    """
    from app.models.rehberlik import RiskSkoruGecmisi

    bugun = date.today()
    if bugune_kayit_garanti:
        risk_snapshot_kaydet(ogrenci_id, bugun=bugun, force=False)
        db.session.commit()

    baslangic = bugun - timedelta(days=hafta_sayisi * 7)
    kayitlar = (RiskSkoruGecmisi.query
                .filter(RiskSkoruGecmisi.ogrenci_id == ogrenci_id,
                        RiskSkoruGecmisi.snapshot_tarih >= baslangic)
                .order_by(RiskSkoruGecmisi.snapshot_tarih.asc())
                .all())

    noktalar = [{
        'tarih': k.snapshot_tarih.strftime('%d.%m.%Y'),
        'tarih_iso': k.snapshot_tarih.isoformat(),
        'skor': k.skor,
        'seviye': k.seviye,
        'devamsizlik_gun': k.devamsizlik_gun,
        'olumsuz_davranis': k.olumsuz_davranis,
        'deneme_trend': k.deneme_trend,
    } for k in kayitlar]

    if len(kayitlar) >= 2:
        ilk, son = kayitlar[0], kayitlar[-1]
        delta = son.skor - ilk.skor
        if delta < -5:
            yon = 'iyilesme'
        elif delta > 5:
            yon = 'kotulesme'
        else:
            yon = 'sabit'
    else:
        delta = 0
        yon = 'yetersiz'

    return {
        'noktalar': noktalar,
        'kayit_sayisi': len(kayitlar),
        'ilk_skor': kayitlar[0].skor if kayitlar else None,
        'son_skor': kayitlar[-1].skor if kayitlar else None,
        'delta': delta,
        'yon': yon,
    }


def risk_listesi(limit: int = 20, esik: int = 30,
                 ogrenci_ids: list[int] | None = None) -> list[dict]:
    """Tum aktif ogrenciler icin risk skorlarini hesaplayip esik ustunde olanlari dondurur.

    Args:
        limit: en yuksek skorlu N ogrenciyi dondur
        esik: bu skorun altindaki ogrenciler listeye eklenmez (varsayilan 30 = orta+)
        ogrenci_ids: belirli bir alt kume icin hesaplama (None ise tum aktifler)
    """
    query = Ogrenci.query.filter_by(aktif=True)
    if ogrenci_ids is not None:
        query = query.filter(Ogrenci.id.in_(ogrenci_ids))
    ogrenciler = query.all()

    bugun = date.today()
    sonuclar: list[dict] = []
    for o in ogrenciler:
        r = ogrenci_risk_skoru(o.id, bugun=bugun)
        if r['skor'] >= esik:
            sonuclar.append(r)

    sonuclar.sort(key=lambda x: -x['skor'])
    return sonuclar[:limit]
