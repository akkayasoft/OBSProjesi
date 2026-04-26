"""Deneme sinavi raporlari: sinav bazli siralama, sube ortalamasi, ogrenci paneli."""
from collections import defaultdict
from flask import Blueprint, render_template, abort
from flask_login import login_required
from sqlalchemy import func

from app.utils import role_required
from app.extensions import db
from app.models.deneme_sinavi import (DenemeSinavi, DenemeDersi,
                                      DenemeKatilim, DenemeDersSonucu)
from app.models.kayit import Sube
from app.models.muhasebe import Ogrenci
from app.models.rehberlik import Gorusme


bp = Blueprint('rapor', __name__, url_prefix='/rapor')


@bp.route('/<int:sinav_id>')
@login_required
@role_required('admin', 'ogretmen')
def sinav_raporu(sinav_id):
    """Bir sinavin genel raporu: siralama, ders ortalamalari, sube ortalamalari."""
    sinav = DenemeSinavi.query.get_or_404(sinav_id)
    dersler = sinav.dersler.all()

    # Tum katilimcilar, puana gore sirali
    katilimlar = (DenemeKatilim.query
                  .filter_by(deneme_sinavi_id=sinav.id, katildi=True)
                  .order_by(DenemeKatilim.toplam_puan.desc().nulls_last())
                  .all())

    # Ders bazli ortalama netler
    ders_ortalamalari = {}
    for ders in dersler:
        ort = db.session.query(func.avg(DenemeDersSonucu.net)).join(
            DenemeKatilim, DenemeKatilim.id == DenemeDersSonucu.katilim_id
        ).filter(
            DenemeKatilim.deneme_sinavi_id == sinav.id,
            DenemeDersSonucu.deneme_dersi_id == ders.id,
        ).scalar()
        ders_ortalamalari[ders.id] = round(ort, 2) if ort else 0.0

    # Sube ortalamalari
    sube_ozetleri = []
    sube_ids = {k.sube_id for k in katilimlar if k.sube_id}
    for sid in sube_ids:
        sube = Sube.query.get(sid)
        if not sube:
            continue
        k_sayi = sum(1 for k in katilimlar if k.sube_id == sid)
        ort_net = sum((k.toplam_net or 0) for k in katilimlar if k.sube_id == sid)
        ort_net = round(ort_net / k_sayi, 2) if k_sayi else 0
        ort_puan = sum((k.toplam_puan or 0) for k in katilimlar if k.sube_id == sid)
        ort_puan = round(ort_puan / k_sayi, 2) if k_sayi else 0
        sube_ozetleri.append({
            'sube': sube,
            'katilimci': k_sayi,
            'ortalama_net': ort_net,
            'ortalama_puan': ort_puan,
        })
    sube_ozetleri.sort(key=lambda x: -x['ortalama_puan'])

    return render_template('deneme_sinavi/rapor.html',
                           sinav=sinav,
                           dersler=dersler,
                           katilimlar=katilimlar,
                           ders_ortalamalari=ders_ortalamalari,
                           sube_ozetleri=sube_ozetleri)


# ---------------------------------------------------------------------------
# Ogrenci-merkezli deneme paneli
# ---------------------------------------------------------------------------

def _ogrenci_oneri_uret(ders_perf, sinavlar):
    """Kural-tabanli otomatik gozlemler/oneriler.

    ders_perf: {ders_kodu: {'ders_adi','soru_sayisi','ortalama_net','sinif_ort','delta','son_netler':[..]}}
    sinavlar: kronolojik DenemeKatilim listesi (eskiden yeniye)
    """
    oneriler = []  # [{'tip': 'uyari'|'guclu'|'bilgi', 'mesaj': '...'}]

    if len(sinavlar) == 0:
        return oneriler

    # 1) Genel trend (son 3 vs onceki)
    if len(sinavlar) >= 4:
        son3 = [s.toplam_net for s in sinavlar[-3:] if s.toplam_net is not None]
        onceki = [s.toplam_net for s in sinavlar[:-3] if s.toplam_net is not None]
        if son3 and onceki:
            son_ort = sum(son3) / len(son3)
            onceki_ort = sum(onceki) / len(onceki)
            if onceki_ort > 0:
                fark_yuzde = (son_ort - onceki_ort) / onceki_ort * 100
                if fark_yuzde >= 10:
                    oneriler.append({
                        'tip': 'guclu',
                        'mesaj': f"Son 3 denemenin toplam net ortalamasi (%{fark_yuzde:.0f}) artmis. Ivme korunmali."
                    })
                elif fark_yuzde <= -10:
                    oneriler.append({
                        'tip': 'uyari',
                        'mesaj': f"Son 3 denemede toplam net ortalamasi %{abs(fark_yuzde):.0f} dusmus. Calisma plani gozden gecirilmeli."
                    })

    # 2) Ders bazli zayif/guclu alanlar
    zayif = []
    guclu = []
    for kod, p in ders_perf.items():
        if p['delta'] is None:
            continue
        # Sinif ortalamasinin >= 1.5 net altinda → zayif
        if p['delta'] <= -1.5:
            zayif.append((p['delta'], p['ders_adi']))
        elif p['delta'] >= 1.5:
            guclu.append((p['delta'], p['ders_adi']))

    if zayif:
        zayif.sort()  # en negatif onde
        adlar = ', '.join(d for _, d in zayif[:3])
        oneriler.append({
            'tip': 'uyari',
            'mesaj': f"Sinif ortalamasinin altinda kalan dersler: {adlar}. Konu tekrari ve ek soru cozumu onerilir."
        })
    if guclu:
        guclu.sort(reverse=True)
        adlar = ', '.join(d for _, d in guclu[:3])
        oneriler.append({
            'tip': 'guclu',
            'mesaj': f"Sinif ortalamasinin uzerinde performans gosterilen dersler: {adlar}. Bu seviyenin korunmasi onemli."
        })

    # 3) Ders icinde dususte olan derslerin tespiti (son 3 net)
    for kod, p in ders_perf.items():
        netler = [n for n in p['son_netler'] if n is not None]
        if len(netler) >= 3:
            ilk_yari = netler[: len(netler) // 2]
            son_yari = netler[len(netler) // 2:]
            if ilk_yari and son_yari:
                fark = (sum(son_yari) / len(son_yari)) - (sum(ilk_yari) / len(ilk_yari))
                if fark <= -1.0:
                    oneriler.append({
                        'tip': 'uyari',
                        'mesaj': f"{p['ders_adi']} dersinde son denemelere dogru net dusmus (-{abs(fark):.1f}). Konu eksigi olabilir."
                    })

    # 4) Yuksek yanlis sayisi (toplam yanlis > toplam dogru'nun yarisi)
    son_sinav = sinavlar[-1]
    if son_sinav.toplam_dogru and son_sinav.toplam_yanlis:
        if son_sinav.toplam_yanlis > son_sinav.toplam_dogru * 0.4:
            oneriler.append({
                'tip': 'uyari',
                'mesaj': "Son denemede yanlis sayisi yuksek. Soru cozum hizini biraz dusurup dogruluk artirilmali."
            })

    # 5) Bos cevap > soru sayisinin %30'u
    if son_sinav.toplam_bos:
        toplam_soru = sum(d['soru_sayisi'] for d in ders_perf.values())
        if toplam_soru and son_sinav.toplam_bos > toplam_soru * 0.30:
            oneriler.append({
                'tip': 'uyari',
                'mesaj': "Son denemede bos cevap orani yuksek (%30+). Zaman yonetimi ve tahmin stratejisi gozden gecirilmeli."
            })

    # 6) Genel iyi durum (hicbir uyari yoksa)
    if not any(o['tip'] == 'uyari' for o in oneriler) and len(sinavlar) >= 2:
        oneriler.append({
            'tip': 'bilgi',
            'mesaj': "Genel performans stabil veya iyilesme egiliminde. Mevcut calisma duzeni surdurulebilir."
        })

    return oneriler


@bp.route('/ogrenci/<int:ogrenci_id>')
@login_required
@role_required('admin', 'ogretmen')
def ogrenci_paneli(ogrenci_id):
    """Bir ogrencinin tum deneme sinavi gecmisi, analiz, oneriler.

    Yoneticinin sinava giren ogrenci listesinden ogrenciye tiklayarak
    ulastigi panel. Trend, ders performansi, otomatik oneriler ve
    rehberlik gorusmeleri ozeti gosterilir.
    """
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)

    # Tum katilimlar (kronolojik: eskiden yeniye)
    katilimlar = (DenemeKatilim.query
                  .join(DenemeSinavi, DenemeSinavi.id == DenemeKatilim.deneme_sinavi_id)
                  .filter(DenemeKatilim.ogrenci_id == ogrenci_id,
                          DenemeKatilim.katildi.is_(True))
                  .order_by(DenemeSinavi.tarih.asc(), DenemeSinavi.id.asc())
                  .all())

    # Her katilim icin sinav siralamasi (1-based) hesapla
    sinav_listesi = []
    for k in katilimlar:
        if k.toplam_puan is not None:
            ust_sayi = (DenemeKatilim.query
                        .filter(DenemeKatilim.deneme_sinavi_id == k.deneme_sinavi_id,
                                DenemeKatilim.katildi.is_(True),
                                DenemeKatilim.toplam_puan > k.toplam_puan)
                        .count())
            siralama = ust_sayi + 1
        else:
            siralama = None
        toplam_katilimci = (DenemeKatilim.query
                            .filter_by(deneme_sinavi_id=k.deneme_sinavi_id, katildi=True)
                            .count())
        sinav_listesi.append({
            'katilim': k,
            'sinav': k.sinav,
            'siralama': siralama,
            'toplam_katilimci': toplam_katilimci,
        })

    # Ders bazli performans aggregate
    # Ders kodlari farkli sinav tiplerinde tekrar edebilir (matematik vs Temel Matematik)
    # Ders_kodu uzerinden toparla.
    ders_acc = defaultdict(lambda: {
        'ders_adi': None,
        'soru_sayisi': 0,
        'netler': [],          # tum sinavlar boyunca
        'son_netler': [],      # son 5 sinav
        'sinif_netleri': [],   # her sinav icin sinif ortalamasi
        'dogru': 0, 'yanlis': 0, 'bos': 0,
    })

    # Son N sinav icin ders sonuc detaylari (son_netler doldurmak icin tarih sirasi)
    son_kac = 5
    son_katilimlar = katilimlar[-son_kac:] if len(katilimlar) > son_kac else katilimlar
    son_katilim_idleri = {k.id for k in son_katilimlar}

    for k in katilimlar:
        for s in k.ders_sonuclari:
            ders = s.ders  # DenemeDersi
            if not ders:
                continue
            kod = ders.ders_kodu
            acc = ders_acc[kod]
            acc['ders_adi'] = ders.ders_adi
            acc['soru_sayisi'] = max(acc['soru_sayisi'], ders.soru_sayisi or 0)
            if s.net is not None:
                acc['netler'].append(s.net)
                if k.id in son_katilim_idleri:
                    acc['son_netler'].append(s.net)
            acc['dogru'] += s.dogru or 0
            acc['yanlis'] += s.yanlis or 0
            acc['bos'] += s.bos or 0

            # O sinavdaki ders icin sinif ortalamasi
            sinif_ort = (db.session.query(func.avg(DenemeDersSonucu.net))
                         .join(DenemeKatilim, DenemeKatilim.id == DenemeDersSonucu.katilim_id)
                         .filter(DenemeKatilim.deneme_sinavi_id == k.deneme_sinavi_id,
                                 DenemeDersSonucu.deneme_dersi_id == ders.id)
                         .scalar())
            if sinif_ort is not None:
                acc['sinif_netleri'].append(float(sinif_ort))

    # Ders performans ozeti hazirla
    ders_performans = {}
    for kod, acc in ders_acc.items():
        netler = acc['netler']
        sinif_netleri = acc['sinif_netleri']
        ortalama = round(sum(netler) / len(netler), 2) if netler else 0.0
        sinif_ort = round(sum(sinif_netleri) / len(sinif_netleri), 2) if sinif_netleri else None
        delta = round(ortalama - sinif_ort, 2) if sinif_ort is not None else None
        ders_performans[kod] = {
            'ders_adi': acc['ders_adi'],
            'soru_sayisi': acc['soru_sayisi'],
            'ortalama_net': ortalama,
            'sinif_ort': sinif_ort,
            'delta': delta,
            'son_netler': acc['son_netler'],
            'dogru': acc['dogru'],
            'yanlis': acc['yanlis'],
            'bos': acc['bos'],
            'sinav_sayisi': len(netler),
        }

    # Ozet metrikler
    netler = [k.toplam_net for k in katilimlar if k.toplam_net is not None]
    puanlar = [k.toplam_puan for k in katilimlar if k.toplam_puan is not None]
    ozet = {
        'sinav_sayisi': len(katilimlar),
        'son_net': netler[-1] if netler else None,
        'son_puan': puanlar[-1] if puanlar else None,
        'ilk_net': netler[0] if netler else None,
        'ilk_puan': puanlar[0] if puanlar else None,
        'en_yuksek_puan': max(puanlar) if puanlar else None,
        'en_dusuk_puan': min(puanlar) if puanlar else None,
        'ortalama_net': round(sum(netler) / len(netler), 2) if netler else None,
        'ortalama_puan': round(sum(puanlar) / len(puanlar), 2) if puanlar else None,
    }
    if ozet['son_puan'] is not None and ozet['ilk_puan'] is not None:
        ozet['gelisim_puan'] = round(ozet['son_puan'] - ozet['ilk_puan'], 2)
    else:
        ozet['gelisim_puan'] = None

    # Otomatik oneriler
    oneriler = _ogrenci_oneri_uret(ders_performans, katilimlar)

    # Trend grafigi icin Chart.js veri seti
    trend_labels = [k.sinav.tarih.strftime('%d.%m.%y') for k in katilimlar]
    trend_net = [k.toplam_net or 0 for k in katilimlar]
    trend_puan = [k.toplam_puan or 0 for k in katilimlar]
    trend_sinav_adlari = [k.sinav.ad for k in katilimlar]

    # Rehberlik ozeti (son 5 gorusme + tum gorusme sayisi)
    son_gorusmeler = (Gorusme.query
                      .filter_by(ogrenci_id=ogrenci_id)
                      .order_by(Gorusme.gorusme_tarihi.desc())
                      .limit(5).all())
    toplam_gorusme_sayisi = Gorusme.query.filter_by(ogrenci_id=ogrenci_id).count()

    return render_template('deneme_sinavi/ogrenci_paneli.html',
                           ogrenci=ogrenci,
                           ozet=ozet,
                           sinav_listesi=sinav_listesi,
                           ders_performans=ders_performans,
                           oneriler=oneriler,
                           trend_labels=trend_labels,
                           trend_net=trend_net,
                           trend_puan=trend_puan,
                           trend_sinav_adlari=trend_sinav_adlari,
                           son_gorusmeler=son_gorusmeler,
                           toplam_gorusme_sayisi=toplam_gorusme_sayisi)
