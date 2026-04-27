"""Veli listesi: dershanedeki tum velileri toplu gorma + duzenleme + arama.

Bir veli birden fazla ogrencinin velisi olabilir (kardesler durumu),
bu sebeple listeyi unique key uzerinden gruplandiriyoruz:
    1. user_id (varsa) — sistem kullanicisi olan veliler
    2. (tc_kimlik) — sistem kullanicisi yoksa TC ile
    3. (telefon, ad+soyad normalize) — TC de yoksa fallback

Erisim: admin + yonetici.
"""
from __future__ import annotations

from collections import defaultdict

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from app.utils import role_required
from app.extensions import db
from app.models.kayit import VeliBilgisi
from app.models.muhasebe import Ogrenci
from app.models.user import User
from app.kayit.forms import VeliForm


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
            'id': ana.id,  # duzenleme icin kanonik kayit id'si
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


# --- Duzenleme ------------------------------------------------------------

def _ayni_velinin_diger_kayitlari(v: VeliBilgisi):
    """Bir veliye ait *tum* VeliBilgisi kayitlarini dondur (kardes durumu).

    user_id varsa onunla, yoksa TC, yoksa (ad+soyad+telefon) ile eslestir.
    """
    qs = VeliBilgisi.query.filter(VeliBilgisi.id != v.id)
    if v.user_id:
        return qs.filter(VeliBilgisi.user_id == v.user_id).all()
    if v.tc_kimlik:
        return qs.filter(VeliBilgisi.tc_kimlik == v.tc_kimlik).all()
    return qs.filter(
        VeliBilgisi.ad == v.ad,
        VeliBilgisi.soyad == v.soyad,
        VeliBilgisi.telefon == v.telefon,
    ).all()


@bp.route('/<int:veli_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'yonetici')
def duzenle(veli_id):
    """Velinin bilgilerini duzenle. Veli birden fazla ogrencide kayitliysa
    'tum kardeslere uygula' onay kutusu ile ayni isim/iletisim bilgileri
    diger kayitlara da yansitilabilir."""
    v = VeliBilgisi.query.get_or_404(veli_id)

    # Kardes durumu: bu velinin ayni ogrenci dışındaki kayitlari
    diger_kayitlar = _ayni_velinin_diger_kayitlari(v)

    form = VeliForm(obj=v)
    if request.method == 'GET':
        # Yakinlik 'diger' degeri formda yoksa default'a dussun
        if v.yakinlik not in ('anne', 'baba', 'vasi', 'diger'):
            form.yakinlik.data = 'diger'

    if form.validate_on_submit():
        # Mevcut kaydi guncelle
        v.yakinlik = form.yakinlik.data
        v.tc_kimlik = (form.tc_kimlik.data or '').strip() or None
        v.ad = form.ad.data.strip()
        v.soyad = form.soyad.data.strip()
        v.telefon = (form.telefon.data or '').strip() or None
        v.email = (form.email.data or '').strip() or None
        v.meslek = (form.meslek.data or '').strip() or None
        v.adres = (form.adres.data or '').strip() or None

        # Tum kardeslere uygulansin mi?
        kardeslere_uygula = request.form.get('kardeslere_uygula') == '1'
        guncellenen_kardes = 0
        if kardeslere_uygula and diger_kayitlar:
            for kk in diger_kayitlar:
                # Yakinlik sabit kalsin (kardesin annesi/babasi farkli olabilir)
                kk.tc_kimlik = v.tc_kimlik
                kk.ad = v.ad
                kk.soyad = v.soyad
                kk.telefon = v.telefon
                kk.email = v.email
                kk.meslek = v.meslek
                kk.adres = v.adres
                guncellenen_kardes += 1

        # Eger user hesabi bagliysa onun da ad/soyad/email'ini senkronize et
        senkronize_user = False
        if v.user_id:
            user = User.query.get(v.user_id)
            if user:
                user.ad = v.ad
                user.soyad = v.soyad
                if v.email:
                    user.email = v.email
                senkronize_user = True

        db.session.commit()

        msg = f'"{v.tam_ad}" velisinin bilgileri guncellendi.'
        if guncellenen_kardes:
            msg += f' {guncellenen_kardes} kardes kayit da senkronize edildi.'
        if senkronize_user:
            msg += ' Sistem kullanici hesabi da guncellendi.'
        flash(msg, 'success')
        return redirect(url_for('kayit.veli.liste'))

    # Bagli ogrenciler (mevcut + kardesler)
    ogrenciler = [v.ogrenci] if v.ogrenci else []
    for kk in diger_kayitlar:
        if kk.ogrenci and kk.ogrenci not in ogrenciler:
            ogrenciler.append(kk.ogrenci)

    return render_template(
        'kayit/veli_duzenle.html',
        form=form,
        veli=v,
        ogrenciler=ogrenciler,
        kardes_kayit_sayisi=len(diger_kayitlar),
    )
