"""OMR (optik form okuma) route'lari.

Akis:
1. Admin cevap anahtarini girer (her ders icin soru_no -> dogru_cevap).
2. Admin optik form sablonunu PDF olarak indirir, cogaltip ogrencilere verir.
3. Sinavdan sonra cevap kagitlarini fotograflar / tarar ve sisteme yukler.
4. OMR pipeline fotografi cozer; her tarama bir `OmrTarama` kaydi olusturur.
5. Okunmus `ogrenci_no` ile ogrenci eslenir, D/Y/B hesaplanip `DenemeKatilim`
   + `DenemeDersSonucu` yaratilir/guncellenir.
"""
import json
import os
from werkzeug.utils import secure_filename

from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, send_file, current_app)
from flask_login import login_required, current_user
from io import BytesIO

from app.utils import role_required
from app.extensions import db
from app.models.deneme_sinavi import (DenemeSinavi, DenemeDersi, DenemeKatilim,
                                      DenemeDersSonucu, CevapAnahtari,
                                      OmrTarama)
from app.models.muhasebe import Ogrenci
from app.models.kayit import OgrenciKayit
from app.omr.pdf_template import generate_answer_sheet_pdf
from app.omr.pipeline import omr_okuma, karsilastir
from app.omr import layout as L


bp = Blueprint('omr', __name__, url_prefix='/sinav/<int:sinav_id>/omr')


ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'webp'}


def _get_sinav_or_404(sinav_id):
    return DenemeSinavi.query.get_or_404(sinav_id)


# --------------------------------------------------------------------------
# Sablon PDF
# --------------------------------------------------------------------------

@bp.route('/sablon.pdf')
@login_required
@role_required('admin', 'ogretmen')
def sablon_pdf(sinav_id):
    sinav = _get_sinav_or_404(sinav_id)
    dersler = sinav.dersler.all()
    toplam_soru = sum((d.soru_sayisi or 0) for d in dersler) or L.MAX_QUESTIONS
    toplam_soru = min(toplam_soru, L.MAX_QUESTIONS)

    # LGS 4 sik, digerleri 5 sik
    sik_sayisi = 4 if sinav.sinav_tipi == 'lgs' else 5

    ders_bilgisi = ' / '.join(f'{d.ders_adi} {d.soru_sayisi}' for d in dersler)
    if not ders_bilgisi:
        ders_bilgisi = f'Toplam {toplam_soru} soru'

    pdf_bytes = generate_answer_sheet_pdf(
        sinav_adi=sinav.ad,
        ders_bilgisi=ders_bilgisi,
        soru_sayisi=toplam_soru,
        sik_sayisi=sik_sayisi,
    )
    buf = BytesIO(pdf_bytes)
    buf.seek(0)
    return send_file(
        buf,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'omr_sablon_sinav_{sinav.id}.pdf',
    )


# --------------------------------------------------------------------------
# Cevap anahtari
# --------------------------------------------------------------------------

@bp.route('/anahtar', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def anahtar(sinav_id):
    sinav = _get_sinav_or_404(sinav_id)
    dersler = sinav.dersler.order_by('sira').all()

    if not dersler:
        flash('Sinav icin once ders bloklari eklenmelidir.', 'warning')
        return redirect(url_for('deneme_sinavi.sinav.detay', sinav_id=sinav.id))

    if request.method == 'POST':
        secenekler = L.ANSWER_OPTIONS
        degisiklik = 0
        for d in dersler:
            # Var olan anahtar kayitlari map
            mevcut = {a.soru_no: a for a in d.cevap_anahtari.all()}
            for s in range(1, (d.soru_sayisi or 0) + 1):
                key = f'd{d.id}_s{s}'
                iptal_key = f'd{d.id}_s{s}_iptal'
                val = (request.form.get(key) or '').strip().upper()
                iptal = bool(request.form.get(iptal_key))
                if val and val not in secenekler:
                    continue  # gecersiz deger, atla
                a = mevcut.get(s)
                if val or iptal:
                    if a is None:
                        a = CevapAnahtari(deneme_dersi_id=d.id, soru_no=s,
                                          dogru_cevap=val or 'A',
                                          iptal=iptal)
                        db.session.add(a)
                        degisiklik += 1
                    else:
                        if a.dogru_cevap != (val or a.dogru_cevap) or a.iptal != iptal:
                            if val:
                                a.dogru_cevap = val
                            a.iptal = iptal
                            degisiklik += 1
                else:
                    # Bos gonderildiyse ve kayit varsa sil
                    if a is not None:
                        db.session.delete(a)
                        degisiklik += 1
        if degisiklik:
            db.session.commit()
            flash(f'{degisiklik} cevap kaydi guncellendi.', 'success')
        else:
            flash('Herhangi bir degisiklik yok.', 'info')
        return redirect(url_for('deneme_sinavi.omr.anahtar', sinav_id=sinav.id))

    # GET: mevcut anahtari yukle
    anahtar_map = {}  # {ders_id: {soru_no: CevapAnahtari}}
    for d in dersler:
        anahtar_map[d.id] = {a.soru_no: a for a in d.cevap_anahtari.all()}

    return render_template('deneme_sinavi/omr_anahtar.html',
                           sinav=sinav,
                           dersler=dersler,
                           anahtar_map=anahtar_map,
                           secenekler=L.ANSWER_OPTIONS,
                           lgs=(sinav.sinav_tipi == 'lgs'))


# --------------------------------------------------------------------------
# Fotograf yukleme + toplu OMR
# --------------------------------------------------------------------------

def _allowed_file(filename: str) -> bool:
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def _upload_dir(sinav_id: int) -> str:
    base = os.path.join(current_app.instance_path, 'omr_uploads',
                        f'sinav_{sinav_id}')
    os.makedirs(base, exist_ok=True)
    return base


def _tum_anahtar(sinav) -> tuple[dict, dict, set]:
    """Sinavdaki tum dersleri birlestiren (global_soru_no) anahtar.

    Uretilen sozluk: {global_soru_no: (ders_id, dogru_cevap, iptal)}
    Ayrica ders_bazli anahtari da doner.
    Global numaralandirma dersin sira sirasina gore: 1. dersin soru_sayisi kadar,
    sonra 2. dersinkiler gelir.
    """
    dersler = sinav.dersler.order_by('sira').all()
    global_map = {}     # global_q -> (ders_id, dogru, iptal)
    ders_anahtar = {}   # ders_id -> {soru_no: dogru}
    ders_iptal = {}     # ders_id -> set(soru_no)
    offset = 0
    for d in dersler:
        ders_anahtar[d.id] = {}
        ders_iptal[d.id] = set()
        for a in d.cevap_anahtari.all():
            ders_anahtar[d.id][a.soru_no] = a.dogru_cevap
            if a.iptal:
                ders_iptal[d.id].add(a.soru_no)
            gq = offset + a.soru_no
            global_map[gq] = (d.id, a.dogru_cevap, a.iptal)
        offset += (d.soru_sayisi or 0)
    return global_map, ders_anahtar, ders_iptal


@bp.route('/yukle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def yukle(sinav_id):
    sinav = _get_sinav_or_404(sinav_id)
    dersler = sinav.dersler.order_by('sira').all()
    toplam_soru = sum((d.soru_sayisi or 0) for d in dersler)

    # Anahtar hazir mi?
    anahtar_eksik = []
    for d in dersler:
        mevcut = d.cevap_anahtari.count()
        if mevcut < (d.soru_sayisi or 0):
            anahtar_eksik.append(
                f'{d.ders_adi}: {mevcut}/{d.soru_sayisi}')

    if request.method == 'POST':
        if anahtar_eksik:
            flash('Cevap anahtari eksik. Once tamamlayin.', 'warning')
            return redirect(url_for('deneme_sinavi.omr.anahtar', sinav_id=sinav.id))

        files = request.files.getlist('fotograflar')
        if not files:
            flash('Dosya secilmedi.', 'warning')
            return redirect(request.url)

        global_map, ders_anahtar, ders_iptal = _tum_anahtar(sinav)
        sik_sayisi = 4 if sinav.sinav_tipi == 'lgs' else 5
        upload_dir = _upload_dir(sinav.id)

        ozet = {'basarili': 0, 'eslenemedi': 0, 'hata': 0}

        for f in files:
            if not f or not f.filename:
                continue
            if not _allowed_file(f.filename):
                ozet['hata'] += 1
                continue
            filename = secure_filename(f.filename)
            save_path = os.path.join(upload_dir, filename)
            f.save(save_path)

            tarama = OmrTarama(
                deneme_sinavi_id=sinav.id,
                dosya_adi=filename,
                durum='bekliyor',
            )
            db.session.add(tarama)
            db.session.flush()

            try:
                res = omr_okuma(
                    image_path=save_path,
                    soru_sayisi=toplam_soru,
                    sik_sayisi=sik_sayisi,
                )
            except Exception as e:
                tarama.durum = 'hata'
                tarama.hata_mesaji = f'OMR okuma hatasi: {e}'
                ozet['hata'] += 1
                db.session.commit()
                continue

            if not res.basarili:
                tarama.durum = 'hata'
                tarama.hata_mesaji = res.hata
                ozet['hata'] += 1
                db.session.commit()
                continue

            tarama.ham_cevaplar_json = res.to_json()
            tarama.ogrenci_no = res.ogrenci_no

            # Ogrenciyi eslestir
            ogr = None
            if res.ogrenci_no:
                ogr = Ogrenci.query.filter_by(ogrenci_no=res.ogrenci_no).first()
            if ogr is None:
                tarama.durum = 'eslenemedi'
                tarama.hata_mesaji = (
                    f'Ogrenci bulunamadi (okunan no: {res.ogrenci_no})'
                    if res.ogrenci_no else
                    'Ogrenci no okunamadi'
                )
                ozet['eslenemedi'] += 1
                db.session.commit()
                continue

            # Global cevap -> ders bazli D/Y/B
            # global_cevap: {global_q: 'A'/None}
            gc = res.cevaplar

            # Katilim upsert
            katilim = DenemeKatilim.query.filter_by(
                deneme_sinavi_id=sinav.id, ogrenci_id=ogr.id
            ).first()
            if katilim is None:
                aktif_kayit = OgrenciKayit.query.filter_by(
                    ogrenci_id=ogr.id, durum='aktif'
                ).first()
                katilim = DenemeKatilim(
                    deneme_sinavi_id=sinav.id,
                    ogrenci_id=ogr.id,
                    sube_id=aktif_kayit.sube_id if aktif_kayit else None,
                    katildi=True,
                )
                db.session.add(katilim)
                db.session.flush()
            else:
                # Var olan ders sonuclarini temizle (yeniden hesaplayacagiz)
                for s in katilim.ders_sonuclari.all():
                    db.session.delete(s)
                db.session.flush()

            offset = 0
            toplam_d = toplam_y = toplam_b = 0
            for d in dersler:
                ders_cevaplari = {}
                for s in range(1, (d.soru_sayisi or 0) + 1):
                    ders_cevaplari[s] = gc.get(offset + s)
                cmp_res = karsilastir(
                    cevaplar=ders_cevaplari,
                    anahtar=ders_anahtar.get(d.id, {}),
                    iptal=ders_iptal.get(d.id, set()),
                )
                sonuc = DenemeDersSonucu(
                    katilim_id=katilim.id,
                    deneme_dersi_id=d.id,
                    dogru=cmp_res['dogru'],
                    yanlis=cmp_res['yanlis'],
                    bos=cmp_res['bos'],
                )
                sonuc.hesapla_net()
                db.session.add(sonuc)
                toplam_d += cmp_res['dogru']
                toplam_y += cmp_res['yanlis']
                toplam_b += cmp_res['bos']
                offset += (d.soru_sayisi or 0)

            katilim.toplam_dogru = toplam_d
            katilim.toplam_yanlis = toplam_y
            katilim.toplam_bos = toplam_b
            katilim.hesapla_toplamlari()

            tarama.katilim_id = katilim.id
            tarama.durum = 'basarili'
            tarama.toplam_dogru = toplam_d
            tarama.toplam_yanlis = toplam_y
            tarama.toplam_bos = toplam_b
            ozet['basarili'] += 1
            db.session.commit()

        flash(
            f'OMR tamamlandi: {ozet["basarili"]} basarili, '
            f'{ozet["eslenemedi"]} eslenemedi, {ozet["hata"]} hata.',
            'info'
        )
        return redirect(url_for('deneme_sinavi.omr.taramalar', sinav_id=sinav.id))

    return render_template('deneme_sinavi/omr_yukle.html',
                           sinav=sinav,
                           toplam_soru=toplam_soru,
                           anahtar_eksik=anahtar_eksik)


# --------------------------------------------------------------------------
# Tarama geçmişi (audit)
# --------------------------------------------------------------------------

@bp.route('/taramalar')
@login_required
@role_required('admin', 'ogretmen')
def taramalar(sinav_id):
    sinav = _get_sinav_or_404(sinav_id)
    kayitlar = (OmrTarama.query
                .filter_by(deneme_sinavi_id=sinav.id)
                .order_by(OmrTarama.created_at.desc())
                .all())
    return render_template('deneme_sinavi/omr_taramalar.html',
                           sinav=sinav, taramalar=kayitlar)
