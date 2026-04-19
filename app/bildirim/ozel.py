"""Ozel Bildirim: hedefli push + in-app bildirim gonderimi.

Akis:
 1. Gonderen (admin/yonetici/muhasebeci/ogretmen) alici filtresi secer:
    - tum aktif ogrenciler / sube bazli / manuel ogrenci listesi
    - her ogrenci icin: ogrenci'ye, veli'ye, ikisine gonderim secenegi
 2. Secilen alici User.id listesi toplanir
 3. Sablon placeholder'lari her alici icin kisiselestirilir
 4. Bildirim (in-app) ve push paralel gonderilir
 5. BildirimGonderim log kaydi yazilir
"""
from __future__ import annotations

from datetime import datetime, date, timedelta
from flask import (render_template, redirect, url_for, flash, request,
                   jsonify, current_app)
from flask_login import login_required, current_user
from sqlalchemy import or_

from app.extensions import db
from app.models.bildirim import (Bildirim, BildirimSablonu, BildirimGonderim,
                                 PushAbonelik)
from app.models.muhasebe import Ogrenci
from app.models.kayit import Sube, Sinif, OgrenciKayit, VeliBilgisi
from app.models.user import User
from app.utils import role_required
from app.utils.push import push_gonder_kullanicilar
from app.bildirim import bildirim_bp


# ---------------------------------------------------------------------------
# Placeholder destegi
# ---------------------------------------------------------------------------

def _ogrenci_baglamı(ogrenci: Ogrenci, veli: VeliBilgisi | None = None) -> dict:
    """Bir ogrenci icin placeholder sozlugu uret."""
    sinif_sube = ogrenci.aktif_sinif_sube or ''
    sinif_parca, sube_parca = '', ''
    if sinif_sube and ' - ' in sinif_sube:
        sinif_parca, sube_parca = sinif_sube.split(' - ', 1)
    return {
        'ad': ogrenci.ad or '',
        'soyad': ogrenci.soyad or '',
        'ogrenci_no': ogrenci.ogrenci_no or '',
        'sinif': sinif_parca,
        'sube': sube_parca,
        'veli_ad': (veli.ad if veli else (ogrenci.veli_ad or '')) or '',
        'veli_soyad': (veli.soyad if veli else '') or '',
    }


def _placeholder_replace(metin: str, baglam: dict) -> str:
    """{ad} vb. placeholder'lari degistir. Tanimsizlar aynen birakilir."""
    if not metin:
        return metin
    sonuc = metin
    for anahtar, deger in baglam.items():
        sonuc = sonuc.replace('{' + anahtar + '}', str(deger or ''))
    return sonuc


# ---------------------------------------------------------------------------
# Yardimci: kullanici kumesi olustur
# ---------------------------------------------------------------------------

def _ogrenci_user_id(ogrenci: Ogrenci) -> int | None:
    return ogrenci.user_id if ogrenci and ogrenci.user_id else None


def _veli_user_idleri(ogrenci: Ogrenci) -> list[int]:
    """Ogrenciye bagli veli User ID'lerini dondur (VeliBilgisi uzerinden)."""
    return [v.user_id for v in ogrenci.veli_bilgileri
            if v.user_id is not None]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@bildirim_bp.route('/ozel/')
@login_required
@role_required('admin', 'yonetici', 'muhasebeci', 'ogretmen')
def ozel_index():
    """Ozel bildirim ana sayfa (alici sec + mesaj yaz)."""
    subeler = Sube.query.filter_by(aktif=True).join(Sinif).order_by(
        Sinif.seviye, Sube.ad).all()
    sablonlar = BildirimSablonu.query.filter_by(aktif=True).order_by(
        BildirimSablonu.kategori, BildirimSablonu.ad).all()
    son_gonderimler = BildirimGonderim.query.order_by(
        BildirimGonderim.created_at.desc()).limit(10).all()
    return render_template('bildirim/ozel_index.html',
                           subeler=subeler,
                           sablonlar=sablonlar,
                           son_gonderimler=son_gonderimler)


@bildirim_bp.route('/ozel/api/ogrenciler')
@login_required
@role_required('admin', 'yonetici', 'muhasebeci', 'ogretmen')
def ozel_api_ogrenciler():
    """Sube/arama filtresiyle ogrenci listesi JSON."""
    sube_id = request.args.get('sube_id', type=int)
    q = (request.args.get('q') or '').strip()

    query = Ogrenci.query.filter_by(aktif=True)

    if sube_id:
        query = (query.join(OgrenciKayit, OgrenciKayit.ogrenci_id == Ogrenci.id)
                 .filter(OgrenciKayit.sube_id == sube_id,
                         OgrenciKayit.durum == 'aktif'))

    if q:
        ilike = f'%{q}%'
        query = query.filter(or_(
            Ogrenci.ad.ilike(ilike),
            Ogrenci.soyad.ilike(ilike),
            Ogrenci.ogrenci_no.ilike(ilike),
        ))

    ogrenciler = query.order_by(Ogrenci.ad, Ogrenci.soyad).limit(300).all()

    sonuc = []
    for o in ogrenciler:
        veli_count = sum(1 for v in o.veli_bilgileri if v.user_id)
        sonuc.append({
            'id': o.id,
            'ad': o.ad,
            'soyad': o.soyad,
            'ogrenci_no': o.ogrenci_no,
            'sinif_sube': o.aktif_sinif_sube or '',
            'has_user': bool(o.user_id),
            'veli_user_count': veli_count,
        })
    return jsonify({'ogrenciler': sonuc})


@bildirim_bp.route('/ozel/gonder', methods=['POST'])
@login_required
@role_required('admin', 'yonetici', 'muhasebeci', 'ogretmen')
def ozel_gonder():
    """Bildirim gonderimini gerceklestir."""
    baslik = (request.form.get('baslik') or '').strip()
    mesaj = (request.form.get('mesaj') or '').strip()
    kategori = (request.form.get('kategori') or 'genel').strip()
    link = (request.form.get('link') or '').strip() or None
    sablon_id = request.form.get('sablon_id', type=int)
    kime = request.form.get('kime', 'ogrenci')  # ogrenci / veli / ikisi
    kaynak = request.form.get('kaynak', 'manuel')

    ogrenci_ids = request.form.getlist('ogrenci_ids', type=int)

    if not baslik or not mesaj:
        flash('Baslik ve mesaj zorunludur.', 'warning')
        return redirect(url_for('bildirim.ozel_index'))
    if not ogrenci_ids:
        flash('En az bir ogrenci secmelisiniz.', 'warning')
        return redirect(url_for('bildirim.ozel_index'))

    ogrenciler = Ogrenci.query.filter(Ogrenci.id.in_(ogrenci_ids),
                                      Ogrenci.aktif.is_(True)).all()

    toplam_alici = 0
    toplam_push = 0

    for o in ogrenciler:
        baglam = _ogrenci_baglamı(o)
        kisisel_baslik = _placeholder_replace(baslik, baglam)
        kisisel_mesaj = _placeholder_replace(mesaj, baglam)

        hedef_user_ids: list[int] = []
        if kime in ('ogrenci', 'ikisi'):
            oid = _ogrenci_user_id(o)
            if oid:
                hedef_user_ids.append(oid)
        if kime in ('veli', 'ikisi'):
            hedef_user_ids.extend(_veli_user_idleri(o))

        # uniq
        hedef_user_ids = list(dict.fromkeys(hedef_user_ids))
        if not hedef_user_ids:
            continue

        # In-app bildirim (toplu)
        Bildirim.toplu_olustur(
            hedef_user_ids,
            baslik=kisisel_baslik,
            mesaj=kisisel_mesaj,
            tur='bilgi',
            kategori='duyuru',
            link=link,
        )

        # Push
        basarili = push_gonder_kullanicilar(
            hedef_user_ids,
            title=kisisel_baslik,
            body=kisisel_mesaj,
            url=link or '/bildirim/',
            tag=f'ozel-{o.id}',
        )

        toplam_alici += len(hedef_user_ids)
        toplam_push += basarili

    # Log
    gonderim = BildirimGonderim(
        gonderen_id=current_user.id,
        sablon_id=sablon_id,
        baslik=baslik,
        mesaj=mesaj,
        kategori=kategori,
        link=link,
        alici_sayisi=toplam_alici,
        push_basarili=toplam_push,
        kaynak=kaynak,
    )
    db.session.add(gonderim)
    db.session.commit()

    flash(f'Bildirim gonderildi: {toplam_alici} alici, {toplam_push} push iletildi.',
          'success')
    return redirect(url_for('bildirim.ozel_index'))


# ---------------------------------------------------------------------------
# Sablon CRUD
# ---------------------------------------------------------------------------

@bildirim_bp.route('/sablon/')
@login_required
@role_required('admin', 'yonetici', 'muhasebeci', 'ogretmen')
def sablon_liste():
    sablonlar = BildirimSablonu.query.order_by(
        BildirimSablonu.sistem.desc(),
        BildirimSablonu.kategori,
        BildirimSablonu.ad,
    ).all()
    return render_template('bildirim/sablon_liste.html',
                           sablonlar=sablonlar,
                           kategoriler=BildirimSablonu.KATEGORILER)


@bildirim_bp.route('/sablon/yeni', methods=['GET', 'POST'])
@bildirim_bp.route('/sablon/<int:id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'yonetici')
def sablon_form(id: int | None = None):
    sablon = BildirimSablonu.query.get_or_404(id) if id else None
    if request.method == 'POST':
        ad = (request.form.get('ad') or '').strip()
        baslik = (request.form.get('baslik') or '').strip()
        mesaj = (request.form.get('mesaj') or '').strip()
        kategori = request.form.get('kategori', 'genel')
        link = (request.form.get('link') or '').strip() or None
        aktif = request.form.get('aktif') == '1'

        if not ad or not baslik or not mesaj:
            flash('Ad, baslik ve mesaj zorunludur.', 'warning')
            return redirect(request.url)

        if sablon is None:
            sablon = BildirimSablonu(olusturan_id=current_user.id)
            db.session.add(sablon)
        elif sablon.sistem and current_user.rol != 'admin':
            flash('Sistem sablonu sadece admin tarafindan duzenlenebilir.', 'warning')
            return redirect(url_for('bildirim.sablon_liste'))

        sablon.ad = ad
        sablon.baslik = baslik
        sablon.mesaj = mesaj
        sablon.kategori = kategori
        sablon.link = link
        sablon.aktif = aktif
        db.session.commit()
        flash('Sablon kaydedildi.', 'success')
        return redirect(url_for('bildirim.sablon_liste'))

    return render_template('bildirim/sablon_form.html',
                           sablon=sablon,
                           kategoriler=BildirimSablonu.KATEGORILER)


@bildirim_bp.route('/sablon/<int:id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'yonetici')
def sablon_sil(id: int):
    sablon = BildirimSablonu.query.get_or_404(id)
    if sablon.sistem and current_user.rol != 'admin':
        flash('Sistem sablonu sadece admin tarafindan silinebilir.', 'warning')
        return redirect(url_for('bildirim.sablon_liste'))
    db.session.delete(sablon)
    db.session.commit()
    flash('Sablon silindi.', 'success')
    return redirect(url_for('bildirim.sablon_liste'))


@bildirim_bp.route('/sablon/<int:id>/json')
@login_required
def sablon_json(id: int):
    """Sablonu JSON olarak dondur (UI'de secince mesaj kutusunu doldurur)."""
    s = BildirimSablonu.query.get_or_404(id)
    return jsonify({
        'id': s.id,
        'ad': s.ad,
        'baslik': s.baslik,
        'mesaj': s.mesaj,
        'kategori': s.kategori,
        'link': s.link or '',
    })


# ---------------------------------------------------------------------------
# Dogum gunu cron
# ---------------------------------------------------------------------------

@bildirim_bp.route('/cron/dogumgunu', methods=['POST', 'GET'])
def cron_dogum_gunu():
    """Bugun dogum gunu olan ogrencilere push + in-app bildirim.

    Guvenlik: ya login (admin/yonetici) ya da CRON_TOKEN (X-Cron-Token header
    veya ?token= query) ile cagrilabilir. Internal — disaridan API olarak
    kullanilmamali.
    """
    token_gecerli = False
    beklenen = current_app.config.get('CRON_TOKEN')
    if beklenen:
        gelen = (request.headers.get('X-Cron-Token')
                 or request.args.get('token'))
        token_gecerli = bool(gelen) and gelen == beklenen

    if not token_gecerli:
        if not current_user.is_authenticated:
            return jsonify({'error': 'auth required'}), 401
        if current_user.rol not in ('admin', 'yonetici'):
            return jsonify({'error': 'forbidden'}), 403

    bugun = date.today()
    # Doğum tarihi bugüne denk gelen aktif öğrenciler (ay/gün karşılaştırması)
    # Bazı DB'lerde EXTRACT yaklaşımı daha güvenli; hem postgres hem sqlite destekli yöntem:
    tum = Ogrenci.query.filter(
        Ogrenci.aktif.is_(True),
        Ogrenci.dogum_tarihi.isnot(None),
    ).all()
    ogrenciler = [o for o in tum
                  if o.dogum_tarihi.month == bugun.month
                  and o.dogum_tarihi.day == bugun.day]

    # Sistemin 'dogum_gunu' sablonu (varsa)
    sablon = BildirimSablonu.query.filter_by(kategori='dogum_gunu',
                                             aktif=True).first()
    varsayilan_baslik = 'Dogum Gunun Kutlu Olsun {ad}!'
    varsayilan_mesaj = ('Sevgili {ad} {soyad}, dogum gununu tum kalbimizle '
                        'kutlariz. Saglikli ve basarili bir yas dilriz.')
    baslik_sbl = sablon.baslik if sablon else varsayilan_baslik
    mesaj_sbl = sablon.mesaj if sablon else varsayilan_mesaj
    link_sbl = (sablon.link if sablon else None) or '/bildirim/'

    toplam_alici = 0
    toplam_push = 0
    for o in ogrenciler:
        baglam = _ogrenci_baglamı(o)
        baslik = _placeholder_replace(baslik_sbl, baglam)
        mesaj = _placeholder_replace(mesaj_sbl, baglam)

        hedefler: list[int] = []
        oid = _ogrenci_user_id(o)
        if oid:
            hedefler.append(oid)
        hedefler.extend(_veli_user_idleri(o))
        hedefler = list(dict.fromkeys(hedefler))
        if not hedefler:
            continue

        Bildirim.toplu_olustur(hedefler, baslik=baslik, mesaj=mesaj,
                               tur='basari', kategori='duyuru', link=link_sbl)
        toplam_push += push_gonder_kullanicilar(
            hedefler, title=baslik, body=mesaj,
            url=link_sbl, tag=f'dogumgunu-{o.id}',
        )
        toplam_alici += len(hedefler)

    log = BildirimGonderim(
        gonderen_id=current_user.id if current_user.is_authenticated else 1,
        sablon_id=sablon.id if sablon else None,
        baslik=baslik_sbl,
        mesaj=mesaj_sbl,
        kategori='dogum_gunu',
        link=link_sbl,
        alici_sayisi=toplam_alici,
        push_basarili=toplam_push,
        kaynak='dogum_gunu_cron',
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'success': True,
        'tarih': bugun.isoformat(),
        'ogrenci_sayisi': len(ogrenciler),
        'alici': toplam_alici,
        'push_basarili': toplam_push,
    })


# ---------------------------------------------------------------------------
# Gecmis / log
# ---------------------------------------------------------------------------

@bildirim_bp.route('/hatirlat/taksit/<int:taksit_id>', methods=['POST'])
@login_required
@role_required('admin', 'yonetici', 'muhasebeci')
def taksit_hatirlat(taksit_id: int):
    """Belirli bir taksit icin ogrenci velisine 'taksit_hatirlatma'
    kategorisindeki aktif sablonla bildirim gonderir."""
    from app.models.muhasebe import Taksit

    taksit = Taksit.query.get_or_404(taksit_id)
    plan = taksit.odeme_plani
    ogrenci = plan.ogrenci

    # Sablon
    sablon = BildirimSablonu.query.filter_by(
        kategori='taksit_hatirlatma', aktif=True
    ).order_by(BildirimSablonu.sistem.desc()).first()

    varsayilan_baslik = '{ad} {soyad} - Yaklasan Taksit'
    varsayilan_mesaj = ('Sayin veli, {ad} {soyad} icin {vade} tarihinde '
                        '{tutar} TL taksit odemesi bulunmaktadir.')
    baslik_sbl = sablon.baslik if sablon else varsayilan_baslik
    mesaj_sbl = sablon.mesaj if sablon else varsayilan_mesaj
    link_sbl = (sablon.link if sablon else None) or '/portal/veli/muhasebe/'

    baglam = _ogrenci_baglamı(ogrenci)
    kalan = float(taksit.tutar) - float(taksit.odenen_tutar)
    baglam['tutar'] = f'{kalan:,.2f}'
    baglam['vade'] = taksit.vade_tarihi.strftime('%d.%m.%Y') if taksit.vade_tarihi else ''

    baslik = _placeholder_replace(baslik_sbl, baglam)
    mesaj = _placeholder_replace(mesaj_sbl, baglam)

    hedefler: list[int] = []
    hedefler.extend(_veli_user_idleri(ogrenci))
    if not hedefler:
        oid = _ogrenci_user_id(ogrenci)
        if oid:
            hedefler.append(oid)
    hedefler = list(dict.fromkeys(hedefler))

    if not hedefler:
        flash('Veli veya ogrenci hesabi bulunamadi — bildirim gonderilemedi.',
              'warning')
        return redirect(request.referrer or url_for(
            'muhasebe.ogrenci_odeme.detay', ogrenci_id=ogrenci.id))

    Bildirim.toplu_olustur(hedefler, baslik=baslik, mesaj=mesaj,
                           tur='uyari', kategori='odeme', link=link_sbl)
    basarili = push_gonder_kullanicilar(
        hedefler, title=baslik, body=mesaj,
        url=link_sbl, tag=f'taksit-{taksit.id}')

    log = BildirimGonderim(
        gonderen_id=current_user.id,
        sablon_id=sablon.id if sablon else None,
        baslik=baslik_sbl,
        mesaj=mesaj_sbl,
        kategori='taksit_hatirlatma',
        link=link_sbl,
        alici_sayisi=len(hedefler),
        push_basarili=basarili,
        kaynak='muhasebe_hatirlat',
    )
    db.session.add(log)
    db.session.commit()

    flash(f'Hatirlatma gonderildi: {len(hedefler)} alici, {basarili} push iletildi.',
          'success')
    return redirect(request.referrer or url_for(
        'muhasebe.ogrenci_odeme.detay', ogrenci_id=ogrenci.id))


@bildirim_bp.route('/ozel/gecmis')
@login_required
@role_required('admin', 'yonetici', 'muhasebeci', 'ogretmen')
def ozel_gecmis():
    page = request.args.get('page', 1, type=int)
    sayfa = BildirimGonderim.query.order_by(
        BildirimGonderim.created_at.desc()
    ).paginate(page=page, per_page=30)
    return render_template('bildirim/ozel_gecmis.html', sayfa=sayfa)
