"""Veli listesi: dershanedeki tum velileri toplu gorma + arama.

Bir veli birden fazla ogrencinin velisi olabilir (kardesler durumu),
bu sebeple listeyi unique key uzerinden gruplandiriyoruz:
    1. user_id (varsa) — sistem kullanicisi olan veliler
    2. (tc_kimlik) — sistem kullanicisi yoksa TC ile
    3. (telefon, ad+soyad normalize) — TC de yoksa fallback

Erisim: admin + yonetici.
"""
from __future__ import annotations

from collections import defaultdict

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.utils import role_required
from app.extensions import db
from app.models.kayit import VeliBilgisi
from app.models.muhasebe import Ogrenci


bp = Blueprint('veli', __name__)


def _norm(s: str | None) -> str:
    if not s:
        return ''
    s = s.strip().lower()
    for a, b in (('ı', 'i'), ('İ', 'i'), ('ş', 's'), ('Ş', 's'),
                 ('ğ', 'g'), ('Ğ', 'g'), ('ü', 'u'), ('Ü', 'u'),
                 ('ö', 'o'), ('Ö', 'o'), ('ç', 'c'), ('Ç', 'c')):
        s = s.replace(a, b)
    return s


def _veli_key(v: VeliBilgisi) -> tuple:
    """Bir velinin unique key'i — birden fazla cocuga sahip olsa bile
    listede tek satir olarak gorunmesi icin gruplandirma anahtari."""
    if v.user_id:
        return ('user', v.user_id)
    if v.tc_kimlik:
        return ('tc', v.tc_kimlik)
    return ('isim', _norm(v.telefon) or '?', _norm(v.ad) + _norm(v.soyad))


@bp.route('/')
@login_required
@role_required('admin', 'yonetici')
def liste():
    arama = (request.args.get('arama') or '').strip()
    yakinlik = (request.args.get('yakinlik') or '').strip()
    page = request.args.get('page', 1, type=int)

    query = (VeliBilgisi.query
             .join(Ogrenci, VeliBilgisi.ogrenci_id == Ogrenci.id)
             .filter(Ogrenci.aktif.is_(True)))

    if yakinlik in ('anne', 'baba', 'vasi'):
        query = query.filter(VeliBilgisi.yakinlik == yakinlik)

    if arama:
        like = f'%{arama}%'
        query = query.filter(
            db.or_(
                VeliBilgisi.ad.ilike(like),
                VeliBilgisi.soyad.ilike(like),
                VeliBilgisi.telefon.ilike(like),
                VeliBilgisi.email.ilike(like),
                VeliBilgisi.tc_kimlik.ilike(like),
                Ogrenci.ad.ilike(like),
                Ogrenci.soyad.ilike(like),
                Ogrenci.ogrenci_no.ilike(like),
            )
        )

    kayitlar = query.order_by(VeliBilgisi.soyad, VeliBilgisi.ad).all()

    # Aynı velinin birden fazla cocugu varsa tek satir olarak grupla
    gruplar: dict = defaultdict(list)
    siralama: list = []
    for v in kayitlar:
        k = _veli_key(v)
        if k not in gruplar:
            siralama.append(k)
        gruplar[k].append(v)

    # Her grup icin kompozit dict olustur
    veliler: list[dict] = []
    for k in siralama:
        items = gruplar[k]
        ana = items[0]  # ilkini "kanonik" olarak kullan
        veliler.append({
            'tam_ad': ana.tam_ad,
            'yakinlik': ana.yakinlik,
            'telefon': ana.telefon,
            'email': ana.email,
            'tc_kimlik': ana.tc_kimlik,
            'meslek': ana.meslek,
            'user_id': ana.user_id,
            'sistem_kullanicisi': ana.user_id is not None,
            'ogrenciler': [
                {
                    'id': v.ogrenci.id,
                    'tam_ad': v.ogrenci.tam_ad,
                    'ogrenci_no': v.ogrenci.ogrenci_no,
                    'sinif': v.ogrenci.aktif_sinif_sube,
                    'yakinlik': v.yakinlik,
                }
                for v in items if v.ogrenci
            ],
        })

    # Basit pagination
    PER_PAGE = 30
    toplam = len(veliler)
    baslangic = (page - 1) * PER_PAGE
    bitis = baslangic + PER_PAGE
    sayfa_veliler = veliler[baslangic:bitis]
    son_sayfa = max(1, (toplam + PER_PAGE - 1) // PER_PAGE)

    # Ozet sayilari
    sistem_kayit_sayisi = sum(1 for v in veliler if v['sistem_kullanicisi'])

    return render_template(
        'kayit/veli_listesi.html',
        veliler=sayfa_veliler,
        toplam=toplam,
        sistem_kayit_sayisi=sistem_kayit_sayisi,
        arama=arama,
        yakinlik=yakinlik,
        page=page,
        son_sayfa=son_sayfa,
        per_page=PER_PAGE,
    )
