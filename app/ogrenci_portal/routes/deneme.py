"""Ogrenci/veli portali deneme (ortak) sinav sonuclari.

Ogrenci veya veli kendi/cocugunun deneme sinav sonuclarini, sube ve
seviye ortalamalariyla birlikte goruntuler.
"""
from flask import Blueprint, render_template, flash, abort
from flask_login import login_required
from sqlalchemy import func

from app.utils import role_required
from app.extensions import db
from app.models.ortak_sinav import OrtakSinav, OrtakSinavSonuc
from app.ogrenci_portal.helpers import get_current_ogrenci


bp = Blueprint('deneme', __name__, url_prefix='/deneme')


@bp.route('/')
@login_required
@role_required('ogrenci', 'veli', 'admin')
def index():
    """Ogrencinin tum deneme sinav sonuclari (tarihe gore)."""
    ogrenci = get_current_ogrenci()
    if not ogrenci:
        flash('Ogrenci kaydiniz bulunamadi.', 'warning')
        return render_template('ogrenci_portal/deneme_liste.html',
                               ogrenci=None, sonuclar=[])

    sonuclar = (
        OrtakSinavSonuc.query
        .filter_by(ogrenci_id=ogrenci.id)
        .join(OrtakSinav, OrtakSinavSonuc.ortak_sinav_id == OrtakSinav.id)
        .order_by(OrtakSinav.tarih.desc())
        .all()
    )

    # Sadece son donemde kac deneme; en yuksek / en dusuk puan ozeti
    toplam = len(sonuclar)
    ortalama = None
    en_yuksek = None
    en_dusuk = None
    if sonuclar:
        puanlar = [s.puan for s in sonuclar if s.puan is not None]
        if puanlar:
            ortalama = round(sum(puanlar) / len(puanlar), 2)
            en_yuksek = max(puanlar)
            en_dusuk = min(puanlar)

    return render_template(
        'ogrenci_portal/deneme_liste.html',
        ogrenci=ogrenci,
        sonuclar=sonuclar,
        toplam=toplam,
        ortalama=ortalama,
        en_yuksek=en_yuksek,
        en_dusuk=en_dusuk,
    )


@bp.route('/<int:sonuc_id>')
@login_required
@role_required('ogrenci', 'veli', 'admin')
def detay(sonuc_id):
    """Tek bir deneme sinav sonucu detayi + sube/seviye ortalamalari + siralama."""
    ogrenci = get_current_ogrenci()
    if not ogrenci:
        flash('Ogrenci kaydiniz bulunamadi.', 'warning')
        abort(404)

    sonuc = OrtakSinavSonuc.query.get_or_404(sonuc_id)

    # Guvenlik: sadece kendi sonucu
    if sonuc.ogrenci_id != ogrenci.id:
        abort(403)

    sinav = OrtakSinav.query.get_or_404(sonuc.ortak_sinav_id)

    # Sube ortalamasi
    sube_ort = db.session.query(func.avg(OrtakSinavSonuc.puan)).filter(
        OrtakSinavSonuc.ortak_sinav_id == sinav.id,
        OrtakSinavSonuc.sube_id == sonuc.sube_id,
    ).scalar()
    sube_ort = round(sube_ort, 2) if sube_ort is not None else None

    # Seviye (tum subeler) ortalamasi
    seviye_ort = db.session.query(func.avg(OrtakSinavSonuc.puan)).filter(
        OrtakSinavSonuc.ortak_sinav_id == sinav.id,
    ).scalar()
    seviye_ort = round(seviye_ort, 2) if seviye_ort is not None else None

    # Siralama: kac ogrenciden kacinci (ayni puanda eslesenler "=" olur)
    tum_puanlar = [
        s.puan for s in OrtakSinavSonuc.query
        .filter(OrtakSinavSonuc.ortak_sinav_id == sinav.id)
        .all()
    ]
    tum_puanlar.sort(reverse=True)
    siralama = None
    if sonuc.puan is not None and tum_puanlar:
        # 1-based rank: kendinden yuksek puan sayisi + 1
        siralama = sum(1 for p in tum_puanlar if p > sonuc.puan) + 1
    katilimci = len(tum_puanlar)

    # Sube icinde siralama
    sube_puanlar = [
        s.puan for s in OrtakSinavSonuc.query
        .filter(
            OrtakSinavSonuc.ortak_sinav_id == sinav.id,
            OrtakSinavSonuc.sube_id == sonuc.sube_id,
        ).all()
    ]
    sube_siralama = None
    if sonuc.puan is not None and sube_puanlar:
        sube_siralama = sum(1 for p in sube_puanlar if p > sonuc.puan) + 1
    sube_katilimci = len(sube_puanlar)

    return render_template(
        'ogrenci_portal/deneme_detay.html',
        ogrenci=ogrenci,
        sonuc=sonuc,
        sinav=sinav,
        sube_ort=sube_ort,
        seviye_ort=seviye_ort,
        siralama=siralama,
        katilimci=katilimci,
        sube_siralama=sube_siralama,
        sube_katilimci=sube_katilimci,
    )
