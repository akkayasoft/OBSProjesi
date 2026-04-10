from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.online_sinav import (OnlineSinav, SinavSoru, SinavKatilim,
                                     OgrenciCevap)
from app.models.muhasebe import Ogrenci

bp = Blueprint('sonuc', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def liste():
    sinavlar = OnlineSinav.query.order_by(OnlineSinav.created_at.desc()).all()
    return render_template('online_sinav/sonuc_listesi.html', sinavlar=sinavlar)


@bp.route('/<int:sinav_id>')
@login_required
@role_required('admin', 'ogretmen')
def sinav_sonuclari(sinav_id):
    sinav = OnlineSinav.query.get_or_404(sinav_id)
    katilimlar = sinav.katilimlar.order_by(SinavKatilim.toplam_puan.desc()).all()

    # Istatistikler
    puanlar = [k.toplam_puan for k in katilimlar if k.toplam_puan is not None]
    ortalama = round(sum(puanlar) / len(puanlar), 1) if puanlar else 0
    en_yuksek = max(puanlar) if puanlar else 0
    en_dusuk = min(puanlar) if puanlar else 0
    medyan = 0
    if puanlar:
        sorted_puanlar = sorted(puanlar)
        n = len(sorted_puanlar)
        if n % 2 == 0:
            medyan = round((sorted_puanlar[n // 2 - 1] + sorted_puanlar[n // 2]) / 2, 1)
        else:
            medyan = sorted_puanlar[n // 2]

    gecen_sayisi = sum(1 for p in puanlar if p >= sinav.gecme_puani)
    kalan_sayisi = len(puanlar) - gecen_sayisi

    # Puan dagilimi (0-10, 10-20, ..., 90-100)
    dagilim = [0] * 10
    for p in puanlar:
        idx = min(int(p // 10), 9)
        dagilim[idx] += 1

    return render_template('online_sinav/sinav_sonuclar.html',
                           sinav=sinav,
                           katilimlar=katilimlar,
                           ortalama=ortalama,
                           en_yuksek=en_yuksek,
                           en_dusuk=en_dusuk,
                           medyan=medyan,
                           gecen_sayisi=gecen_sayisi,
                           kalan_sayisi=kalan_sayisi,
                           dagilim=dagilim)


@bp.route('/<int:sinav_id>/ogrenci/<int:ogrenci_id>')
@login_required
@role_required('admin', 'ogretmen')
def ogrenci_sonuc(sinav_id, ogrenci_id):
    sinav = OnlineSinav.query.get_or_404(sinav_id)
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)
    katilim = SinavKatilim.query.filter_by(
        sinav_id=sinav.id, ogrenci_id=ogrenci_id
    ).first_or_404()

    sorular = sinav.sorular.order_by(SinavSoru.sira).all()
    cevaplar = {}
    for cevap in katilim.cevaplar.all():
        cevaplar[cevap.soru_id] = cevap

    return render_template('online_sinav/ogrenci_sonuc.html',
                           sinav=sinav,
                           ogrenci=ogrenci,
                           katilim=katilim,
                           sorular=sorular,
                           cevaplar=cevaplar)


@bp.route('/<int:katilim_id>/puanla', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def puanla(katilim_id):
    katilim = SinavKatilim.query.get_or_404(katilim_id)
    sinav = katilim.sinav
    ogrenci = katilim.ogrenci

    # Sadece klasik sorularin cevaplarini getir
    klasik_sorular = sinav.sorular.filter(SinavSoru.soru_turu == 'klasik').order_by(SinavSoru.sira).all()
    cevaplar = {}
    for cevap in katilim.cevaplar.all():
        cevaplar[cevap.soru_id] = cevap

    if request.method == 'POST':
        toplam = 0
        for soru in sinav.sorular.all():
            cevap = cevaplar.get(soru.id)
            if cevap:
                if soru.soru_turu == 'klasik':
                    puan_val = request.form.get(f'puan_{soru.id}', type=float)
                    if puan_val is not None:
                        cevap.puan = min(puan_val, soru.puan)
                        cevap.dogru_mu = (puan_val > 0)
                        toplam += cevap.puan
                elif cevap.puan is not None:
                    toplam += cevap.puan

        katilim.toplam_puan = toplam
        db.session.commit()
        flash('Puanlama başarıyla kaydedildi.', 'success')
        return redirect(url_for('online_sinav.sonuc.sinav_sonuclari', sinav_id=sinav.id))

    return render_template('online_sinav/puanlama.html',
                           sinav=sinav,
                           ogrenci=ogrenci,
                           katilim=katilim,
                           klasik_sorular=klasik_sorular,
                           cevaplar=cevaplar)
