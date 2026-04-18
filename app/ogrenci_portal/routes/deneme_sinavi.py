"""Ogrenci/veli portali - yeni Deneme Sinavi (YKS/LGS) sonuclari.

Ogrenci veya veli, kendi/cocugunun deneme sinav katilimlarini (TYT/AYT/LGS vb.)
ders bazli D/Y/B/net, toplam puan, sube/seviye siralamasi ile goruntuler.
"""
from flask import Blueprint, render_template, flash, abort
from flask_login import login_required
from sqlalchemy import func

from app.utils import role_required
from app.extensions import db
from app.models.deneme_sinavi import (DenemeSinavi, DenemeDersi,
                                      DenemeKatilim, DenemeDersSonucu)
from app.ogrenci_portal.helpers import get_current_ogrenci
from app.rehberlik.akademik_analiz import ogrenci_analizi


bp = Blueprint('deneme_sinavi_portal', __name__, url_prefix='/deneme-sinavi')


@bp.route('/')
@login_required
@role_required('ogrenci', 'veli', 'admin')
def index():
    """Ogrencinin tum deneme sinav katilimlari + ilerleme ozeti."""
    ogrenci = get_current_ogrenci()
    if not ogrenci:
        flash('Ogrenci kaydiniz bulunamadi.', 'warning')
        return render_template('ogrenci_portal/deneme_sinavi_liste.html',
                               ogrenci=None, katilimlar=[])

    katilimlar = (
        DenemeKatilim.query
        .filter_by(ogrenci_id=ogrenci.id, katildi=True)
        .join(DenemeSinavi, DenemeKatilim.deneme_sinavi_id == DenemeSinavi.id)
        # Sadece uygulanmis ve tamamlanmis sinavlar ogrenciye gorunsun
        .filter(DenemeSinavi.durum.in_(['uygulandi', 'tamamlandi']))
        .order_by(DenemeSinavi.tarih.desc())
        .all()
    )

    toplam = len(katilimlar)
    ortalama_net = None
    ortalama_puan = None
    en_yuksek_puan = None
    en_dusuk_puan = None
    if katilimlar:
        netler = [k.toplam_net for k in katilimlar if k.toplam_net is not None]
        puanlar = [k.toplam_puan for k in katilimlar if k.toplam_puan is not None]
        if netler:
            ortalama_net = round(sum(netler) / len(netler), 2)
        if puanlar:
            ortalama_puan = round(sum(puanlar) / len(puanlar), 2)
            en_yuksek_puan = max(puanlar)
            en_dusuk_puan = min(puanlar)

    # Chart.js icin veri (tarih sirasiyla)
    # Kronolojik goster (eskiden yeniye)
    chart_sorted = sorted(
        katilimlar,
        key=lambda k: k.sinav.tarih if k.sinav else None
    )
    chart_labels = [k.sinav.tarih.strftime('%d.%m.%Y') for k in chart_sorted if k.sinav]
    chart_puan = [k.toplam_puan or 0 for k in chart_sorted]
    chart_net = [k.toplam_net or 0 for k in chart_sorted]
    chart_sinav_adlari = [k.sinav.ad for k in chart_sorted if k.sinav]

    return render_template(
        'ogrenci_portal/deneme_sinavi_liste.html',
        ogrenci=ogrenci,
        katilimlar=katilimlar,
        toplam=toplam,
        ortalama_net=ortalama_net,
        ortalama_puan=ortalama_puan,
        en_yuksek_puan=en_yuksek_puan,
        en_dusuk_puan=en_dusuk_puan,
        chart_labels=chart_labels,
        chart_puan=chart_puan,
        chart_net=chart_net,
        chart_sinav_adlari=chart_sinav_adlari,
    )


@bp.route('/<int:katilim_id>')
@login_required
@role_required('ogrenci', 'veli', 'admin')
def detay(katilim_id):
    """Tek bir deneme sinav katilim detayi: ders bazli D/Y/B/net + siralama."""
    ogrenci = get_current_ogrenci()
    if not ogrenci:
        flash('Ogrenci kaydiniz bulunamadi.', 'warning')
        abort(404)

    katilim = DenemeKatilim.query.get_or_404(katilim_id)

    # Guvenlik: sadece kendi katilimi
    if katilim.ogrenci_id != ogrenci.id:
        abort(403)

    sinav = katilim.sinav
    if sinav.durum not in ('uygulandi', 'tamamlandi'):
        flash('Bu sinavin sonuclari henuz yayinlanmadi.', 'warning')
        abort(404)

    dersler = sinav.dersler.all()

    # Ders sonuclarini dict'e al
    ders_sonuc_map = {}
    for s in katilim.ders_sonuclari:
        ders_sonuc_map[s.deneme_dersi_id] = s

    # Her ders icin seviye (tum katilimcilar) ortalamasi ve sube ortalamasi
    ders_istatistikleri = []
    for d in dersler:
        # Seviye (tum subeler) ortalama net
        seviye_ort = db.session.query(func.avg(DenemeDersSonucu.net)).join(
            DenemeKatilim, DenemeKatilim.id == DenemeDersSonucu.katilim_id
        ).filter(
            DenemeKatilim.deneme_sinavi_id == sinav.id,
            DenemeDersSonucu.deneme_dersi_id == d.id,
        ).scalar()

        # Sube ortalama net
        sube_ort = None
        if katilim.sube_id:
            sube_ort = db.session.query(func.avg(DenemeDersSonucu.net)).join(
                DenemeKatilim, DenemeKatilim.id == DenemeDersSonucu.katilim_id
            ).filter(
                DenemeKatilim.deneme_sinavi_id == sinav.id,
                DenemeKatilim.sube_id == katilim.sube_id,
                DenemeDersSonucu.deneme_dersi_id == d.id,
            ).scalar()

        sonuc = ders_sonuc_map.get(d.id)
        ders_istatistikleri.append({
            'ders': d,
            'sonuc': sonuc,
            'seviye_ort': round(seviye_ort, 2) if seviye_ort is not None else None,
            'sube_ort': round(sube_ort, 2) if sube_ort is not None else None,
        })

    # Seviye (tum) ortalama puan + siralama
    tum_puanlar = [
        k.toplam_puan for k in DenemeKatilim.query
        .filter(DenemeKatilim.deneme_sinavi_id == sinav.id,
                DenemeKatilim.katildi.is_(True),
                DenemeKatilim.toplam_puan.isnot(None))
        .all()
    ]
    siralama = None
    seviye_puan_ort = None
    if tum_puanlar:
        seviye_puan_ort = round(sum(tum_puanlar) / len(tum_puanlar), 2)
        if katilim.toplam_puan is not None:
            siralama = sum(1 for p in tum_puanlar if p > katilim.toplam_puan) + 1
    katilimci = len(tum_puanlar)

    # Sube icinde siralama ve ortalama
    sube_puanlar = []
    if katilim.sube_id:
        sube_puanlar = [
            k.toplam_puan for k in DenemeKatilim.query
            .filter(DenemeKatilim.deneme_sinavi_id == sinav.id,
                    DenemeKatilim.sube_id == katilim.sube_id,
                    DenemeKatilim.katildi.is_(True),
                    DenemeKatilim.toplam_puan.isnot(None))
            .all()
        ]
    sube_siralama = None
    sube_puan_ort = None
    if sube_puanlar:
        sube_puan_ort = round(sum(sube_puanlar) / len(sube_puanlar), 2)
        if katilim.toplam_puan is not None:
            sube_siralama = sum(1 for p in sube_puanlar if p > katilim.toplam_puan) + 1
    sube_katilimci = len(sube_puanlar)

    # Ogrenciye ozel rehberlik analizi (guclu/zayif ders + motivasyon)
    akademik = ogrenci_analizi(ogrenci.id)

    return render_template(
        'ogrenci_portal/deneme_sinavi_detay.html',
        ogrenci=ogrenci,
        katilim=katilim,
        sinav=sinav,
        ders_istatistikleri=ders_istatistikleri,
        seviye_puan_ort=seviye_puan_ort,
        siralama=siralama,
        katilimci=katilimci,
        sube_puan_ort=sube_puan_ort,
        sube_siralama=sube_siralama,
        sube_katilimci=sube_katilimci,
        akademik=akademik,
    )
