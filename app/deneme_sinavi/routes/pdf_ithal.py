"""Yayinci PDF'inden deneme sinav sonuclarini ice aktarma.

Flow:
  1. /sinav/pdf-ithal/yukle  (GET + POST)
     - PDF dosyasi + yayinci secilir. POST ile parse edilir.
  2. parse sonucu base64 JSON olarak onizleme ekrani render edilir
     (/sinav/pdf-ithal/onizleme, aslinda 1. endpoint POST yaniti).
  3. /sinav/pdf-ithal/onayla  (POST)
     - Gizli JSON + kullanici girdigi ad/tarih/donem ile
       DenemeSinavi, DenemeDersi, DenemeKatilim, DenemeDersSonucu olustur.
"""
from __future__ import annotations
import base64
import json
from datetime import date

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.utils import role_required
from app.extensions import db
from app.models.deneme_sinavi import (
    DenemeSinavi, DenemeDersi, DenemeKatilim, DenemeDersSonucu,
)
from app.models.muhasebe import Ogrenci
from app.deneme_sinavi.forms import PdfIthalatYukleForm, PdfIthalatOnaylaForm
from app.deneme_sinavi.sablonlar import varsayilan_dersler
from app.deneme_sinavi.pdf_ithalat import (
    parse_pdf, DEFAULT_DERS_KODLARI, PdfIthalatSonuc,
)


bp = Blueprint('pdf_ithal', __name__, url_prefix='/pdf-ithal')


def _eslestir_ogrenciler(satirlar):
    """PDF satirlarini sistemdeki Ogrenci kayitlariyla eslestir.

    Stratejiler (sirasiyla):
      1. ogrenci_no (PDF'te 0 degilse) → Ogrenci.ogrenci_no tam eslesme
      2. isim + soyadi normalize ederek tam eslesme (fuzzy degil — basit)

    Doner: satir indeksine karsilik gelen Ogrenci (veya None) listesi.
    """
    from sqlalchemy import func

    ogrenciler = Ogrenci.query.filter_by(aktif=True).all()
    by_no = {o.ogrenci_no: o for o in ogrenciler if o.ogrenci_no}
    # Normalize: "HACI OK" -> "haciok" — bosluklari at, kucuk harf, Turkce
    def _norm(s: str) -> str:
        s = (s or '').strip().lower()
        for a, b in (('ı', 'i'), ('İ', 'i'), ('ş', 's'), ('Ş', 's'),
                     ('ğ', 'g'), ('Ğ', 'g'), ('ü', 'u'), ('Ü', 'u'),
                     ('ö', 'o'), ('Ö', 'o'), ('ç', 'c'), ('Ç', 'c')):
            s = s.replace(a, b)
        return ''.join(ch for ch in s if ch.isalpha())

    by_isim = {}
    for o in ogrenciler:
        key = _norm(f'{o.ad} {o.soyad}')
        by_isim[key] = o

    matches = []
    for r in satirlar:
        m = None
        # 1) ogrenci_no
        if r['ogrenci_no'] and r['ogrenci_no'] != 0:
            m = by_no.get(str(r['ogrenci_no']))
        # 2) isim normalize
        if m is None:
            m = by_isim.get(_norm(r['isim']))
        matches.append(m)
    return matches


def _sonuc_to_dict(sonuc: PdfIthalatSonuc) -> dict:
    return {
        'sinav_adi': sonuc.sinav_adi,
        'okul_adi': sonuc.okul_adi,
        'il': sonuc.il,
        'ilce': sonuc.ilce,
        'satirlar': [
            {
                'sira': r.sira, 'ogrenci_no': r.ogrenci_no,
                'isim': r.isim, 'sinif': r.sinif,
                'dersler': r.dersler,
                'toplam_dogru': r.toplam_dogru,
                'toplam_yanlis': r.toplam_yanlis,
                'toplam_net': r.toplam_net,
                'puan': r.puan,
            }
            for r in sonuc.satirlar
        ],
        'atlananlar': sonuc.atlananlar,
    }


def _dict_to_payload(d: dict) -> str:
    """PDF parse sonucunu hidden form input icin base64 kodla."""
    return base64.b64encode(
        json.dumps(d, ensure_ascii=False).encode('utf-8')
    ).decode('ascii')


def _payload_to_dict(payload: str) -> dict:
    return json.loads(base64.b64decode(payload.encode('ascii')).decode('utf-8'))


@bp.route('/yukle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def yukle():
    form = PdfIthalatYukleForm()
    onayla_form = None
    parse_sonuc = None
    eslesenler = []
    eslesmeyenler = []
    payload_b64 = None

    if form.validate_on_submit():
        pdf_bytes = form.pdf.data.read()
        try:
            parse_sonuc = parse_pdf(pdf_bytes)
        except Exception as e:
            flash(f'PDF okunamadi: {e}', 'danger')
            return redirect(url_for('deneme_sinavi.pdf_ithal.yukle'))

        if not parse_sonuc.satirlar:
            flash('PDF icinde ogrenci satiri bulunamadi. '
                  'Format uyumsuz olabilir.', 'warning')
            return redirect(url_for('deneme_sinavi.pdf_ithal.yukle'))

        # Ogrencileri eslestir
        ogrenciler = _eslestir_ogrenciler(
            [{'ogrenci_no': r.ogrenci_no, 'isim': r.isim}
             for r in parse_sonuc.satirlar]
        )
        for r, o in zip(parse_sonuc.satirlar, ogrenciler):
            row = {
                'sira': r.sira, 'ogrenci_no': r.ogrenci_no,
                'isim': r.isim, 'sinif': r.sinif, 'puan': r.puan,
                'toplam_net': r.toplam_net,
                'eslesme': (f'{o.ogrenci_no} — {o.tam_ad}' if o else None),
                'eslesme_id': (o.id if o else None),
            }
            if o:
                eslesenler.append(row)
            else:
                eslesmeyenler.append(row)

        # Onay formu
        onayla_form = PdfIthalatOnaylaForm(
            sinav_adi=parse_sonuc.sinav_adi or 'Deneme Sinavi',
            tarih=date.today(),
        )

        # Hidden payload: parse sonucu + eslesme id'leri
        ithalat_dict = _sonuc_to_dict(parse_sonuc)
        ithalat_dict['eslesme_ids'] = [o.id if o else None for o in ogrenciler]
        payload_b64 = _dict_to_payload(ithalat_dict)

    return render_template(
        'deneme_sinavi/pdf_ithal.html',
        form=form, onayla_form=onayla_form,
        parse_sonuc=parse_sonuc,
        eslesenler=eslesenler,
        eslesmeyenler=eslesmeyenler,
        payload=payload_b64,
    )


@bp.route('/onayla', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def onayla():
    onayla_form = PdfIthalatOnaylaForm()
    payload_b64 = request.form.get('payload', '')
    if not payload_b64:
        flash('Ithalat verisi bulunamadi, lutfen PDF\'i yeniden yukleyin.', 'danger')
        return redirect(url_for('deneme_sinavi.pdf_ithal.yukle'))

    try:
        data = _payload_to_dict(payload_b64)
    except Exception:
        flash('Ithalat verisi bozuk, lutfen PDF\'i yeniden yukleyin.', 'danger')
        return redirect(url_for('deneme_sinavi.pdf_ithal.yukle'))

    if not onayla_form.validate_on_submit():
        flash('Form hatali: sinav adi, tarih ve donem zorunlu.', 'danger')
        return redirect(url_for('deneme_sinavi.pdf_ithal.yukle'))

    sinav_adi = onayla_form.sinav_adi.data.strip()
    donem = onayla_form.donem.data.strip()
    tarih = onayla_form.tarih.data

    # Ayni ad + tarih varsa engelle
    mevcut = DenemeSinavi.query.filter_by(
        ad=sinav_adi, tarih=tarih, sinav_tipi='lgs'
    ).first()
    if mevcut:
        flash(f'Ayni ad ve tarihte LGS denemesi zaten var: "{mevcut.ad}". '
              'Iptal edildi.', 'warning')
        return redirect(url_for('deneme_sinavi.sinav.detay', sinav_id=mevcut.id))

    # 1) DenemeSinavi
    sinav = DenemeSinavi(
        ad=sinav_adi, sinav_tipi='lgs', donem=donem, tarih=tarih,
        hedef_seviye='8', sure_dakika=155, durum='tamamlandi',
        aciklama=(f'PDF ithalat ({data.get("okul_adi") or "?"}) — '
                  f'{len(data.get("satirlar", []))} ogrenci'),
        olusturan_id=current_user.id,
    )
    db.session.add(sinav)
    db.session.flush()

    # 2) 6 ders blogu (LGS sablon)
    dersler_meta = {d['ders_kodu']: d for d in varsayilan_dersler('lgs')}
    ders_by_kod = {}
    for sira, kod in enumerate(DEFAULT_DERS_KODLARI, 1):
        meta = dersler_meta.get(kod)
        if not meta:
            continue
        ders = DenemeDersi(
            deneme_sinavi_id=sinav.id,
            ders_kodu=meta['ders_kodu'], ders_adi=meta['ders_adi'],
            soru_sayisi=meta['soru_sayisi'], katsayi=meta['katsayi'],
            alan=meta['alan'], sira=sira,
        )
        db.session.add(ders)
        db.session.flush()
        ders_by_kod[kod] = ders

    # 3) Her ogrenci icin katilim + ders sonuclari
    satirlar = data.get('satirlar', [])
    eslesme_ids = data.get('eslesme_ids', [])
    kaydedilen = 0
    atlanan_eslemedi = 0
    for r, og_id in zip(satirlar, eslesme_ids):
        if not og_id:
            atlanan_eslemedi += 1
            continue
        katilim = DenemeKatilim(
            deneme_sinavi_id=sinav.id,
            ogrenci_id=og_id,
            katildi=True,
            toplam_dogru=r['toplam_dogru'],
            toplam_yanlis=r['toplam_yanlis'],
            toplam_bos=None,  # PDF'te yok
            toplam_net=r['toplam_net'],
            toplam_puan=r['puan'],
        )
        db.session.add(katilim)
        db.session.flush()

        # Her ders icin DenemeDersSonucu
        for i, (d, y, n) in enumerate(r['dersler']):
            if i >= len(DEFAULT_DERS_KODLARI):
                break
            kod = DEFAULT_DERS_KODLARI[i]
            ders = ders_by_kod.get(kod)
            if not ders:
                continue
            # bos = soru_sayisi - (d + y)
            bos = max(ders.soru_sayisi - d - y, 0)
            ds = DenemeDersSonucu(
                katilim_id=katilim.id,
                deneme_dersi_id=ders.id,
                dogru=d, yanlis=y, bos=bos, net=n,
            )
            db.session.add(ds)
        kaydedilen += 1

    db.session.commit()

    msg = (f'LGS denemesi olusturuldu: {kaydedilen} ogrenci kaydedildi.')
    if atlanan_eslemedi:
        msg += f' {atlanan_eslemedi} ogrenci sistemde bulunamadigi icin atlandi.'
    flash(msg, 'success')
    return redirect(url_for('deneme_sinavi.sinav.detay', sinav_id=sinav.id))
