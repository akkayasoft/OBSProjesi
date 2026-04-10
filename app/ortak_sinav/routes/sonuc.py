from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.ortak_sinav import OrtakSinav, OrtakSinavSonuc
from app.models.muhasebe import Ogrenci
from app.models.kayit import Sinif, Sube, OgrenciKayit
from app.ortak_sinav.forms import SonucGirisiForm

bp = Blueprint('sonuc', __name__)


@bp.route('/<int:sinav_id>/giris', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def giris(sinav_id):
    sinav = OrtakSinav.query.get_or_404(sinav_id)
    form = SonucGirisiForm()

    # Sinav seviyesine gore subeleri getir
    subeler = Sube.query.join(Sinif).filter(
        Sinif.seviye == sinav.seviye,
        Sube.aktif == True
    ).order_by(Sinif.ad, Sube.ad).all()

    form.sube_id.choices = [
        (s.id, s.tam_ad) for s in subeler
    ]

    # Aktif ogrencileri getir
    ogrenciler = Ogrenci.query.join(OgrenciKayit).join(Sube).join(Sinif).filter(
        Sinif.seviye == sinav.seviye,
        OgrenciKayit.durum == 'aktif',
        Ogrenci.aktif == True
    ).order_by(Ogrenci.ad).all()

    form.ogrenci_id.choices = [
        (o.id, f'{o.ogrenci_no} - {o.tam_ad}') for o in ogrenciler
    ]

    if form.validate_on_submit():
        # Ayni ogrenci icin daha once sonuc girilmis mi kontrol et
        mevcut = OrtakSinavSonuc.query.filter_by(
            ortak_sinav_id=sinav.id,
            ogrenci_id=form.ogrenci_id.data
        ).first()

        if mevcut:
            mevcut.puan = form.puan.data
            mevcut.sube_id = form.sube_id.data
            mevcut.dogru_sayisi = form.dogru_sayisi.data
            mevcut.yanlis_sayisi = form.yanlis_sayisi.data
            mevcut.bos_sayisi = form.bos_sayisi.data
            flash('Sonuc basariyla guncellendi.', 'success')
        else:
            sonuc = OrtakSinavSonuc(
                ortak_sinav_id=sinav.id,
                ogrenci_id=form.ogrenci_id.data,
                sube_id=form.sube_id.data,
                puan=form.puan.data,
                dogru_sayisi=form.dogru_sayisi.data,
                yanlis_sayisi=form.yanlis_sayisi.data,
                bos_sayisi=form.bos_sayisi.data,
            )
            db.session.add(sonuc)
            flash('Sonuc basariyla kaydedildi.', 'success')

        db.session.commit()
        return redirect(url_for('ortak_sinav.sonuc.giris', sinav_id=sinav.id))

    return render_template('ortak_sinav/sonuc_girisi.html',
                           sinav=sinav, form=form, subeler=subeler)


@bp.route('/<int:sinav_id>/toplu/<int:sube_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def toplu_giris(sinav_id, sube_id):
    sinav = OrtakSinav.query.get_or_404(sinav_id)
    sube = Sube.query.get_or_404(sube_id)

    # Subeye kayitli aktif ogrencileri getir
    kayitlar = OgrenciKayit.query.filter_by(
        sube_id=sube.id,
        durum='aktif'
    ).all()
    ogrenciler = [k.ogrenci for k in kayitlar if k.ogrenci.aktif]
    ogrenciler.sort(key=lambda o: (o.ad, o.soyad))

    # Mevcut sonuclari getir
    mevcut_sonuclar = {}
    for s in OrtakSinavSonuc.query.filter_by(
        ortak_sinav_id=sinav.id, sube_id=sube.id
    ).all():
        mevcut_sonuclar[s.ogrenci_id] = s

    if request.method == 'POST':
        kaydedilen = 0
        for ogrenci in ogrenciler:
            puan_str = request.form.get(f'puan_{ogrenci.id}', '').strip()
            if not puan_str:
                continue

            try:
                puan = float(puan_str)
            except ValueError:
                continue

            dogru = request.form.get(f'dogru_{ogrenci.id}', '').strip()
            yanlis = request.form.get(f'yanlis_{ogrenci.id}', '').strip()
            bos = request.form.get(f'bos_{ogrenci.id}', '').strip()

            dogru_val = int(dogru) if dogru else None
            yanlis_val = int(yanlis) if yanlis else None
            bos_val = int(bos) if bos else None

            if ogrenci.id in mevcut_sonuclar:
                sonuc = mevcut_sonuclar[ogrenci.id]
                sonuc.puan = puan
                sonuc.dogru_sayisi = dogru_val
                sonuc.yanlis_sayisi = yanlis_val
                sonuc.bos_sayisi = bos_val
            else:
                sonuc = OrtakSinavSonuc(
                    ortak_sinav_id=sinav.id,
                    ogrenci_id=ogrenci.id,
                    sube_id=sube.id,
                    puan=puan,
                    dogru_sayisi=dogru_val,
                    yanlis_sayisi=yanlis_val,
                    bos_sayisi=bos_val,
                )
                db.session.add(sonuc)
            kaydedilen += 1

        db.session.commit()
        flash(f'{kaydedilen} ogrenci icin sonuc kaydedildi.', 'success')
        return redirect(url_for('ortak_sinav.sonuc.toplu_giris',
                                sinav_id=sinav.id, sube_id=sube.id))

    # Sinav seviyesine gore subeleri getir (sidebar navigation)
    subeler = Sube.query.join(Sinif).filter(
        Sinif.seviye == sinav.seviye,
        Sube.aktif == True
    ).order_by(Sinif.ad, Sube.ad).all()

    return render_template('ortak_sinav/sonuc_girisi.html',
                           sinav=sinav,
                           sube=sube,
                           subeler=subeler,
                           ogrenciler=ogrenciler,
                           mevcut_sonuclar=mevcut_sonuclar,
                           toplu=True,
                           form=None)


@bp.route('/sil/<int:sonuc_id>', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def sil(sonuc_id):
    sonuc = OrtakSinavSonuc.query.get_or_404(sonuc_id)
    sinav_id = sonuc.ortak_sinav_id
    db.session.delete(sonuc)
    db.session.commit()
    flash('Sonuc silindi.', 'success')
    return redirect(url_for('ortak_sinav.sinav.detay', sinav_id=sinav_id))
