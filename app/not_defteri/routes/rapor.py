from flask import Blueprint, render_template, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.not_defteri import Sinav, OgrenciNot
from app.models.ders_dagitimi import Ders
from app.models.muhasebe import Ogrenci
from app.models.kayit import Sinif, Sube, OgrenciKayit

bp = Blueprint('rapor', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def index():
    ogrenciler = Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad, Ogrenci.soyad).all()
    subeler = Sube.query.join(Sube.sinif).filter(
        Sube.aktif == True
    ).order_by(Sinif.seviye, Sube.ad).all()

    return render_template('not_defteri/rapor.html',
                           ogrenciler=ogrenciler,
                           subeler=subeler)


@bp.route('/ogrenci/<int:ogrenci_id>')
@login_required
@role_required('admin', 'ogretmen')
def ogrenci_karnesi(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)

    # Öğrencinin tüm notlarını derslere göre grupla
    notlar = OgrenciNot.query.filter_by(ogrenci_id=ogrenci_id).filter(
        OgrenciNot.puan.isnot(None)
    ).all()

    # Derslere göre grupla
    ders_notlari = {}
    for not_kaydi in notlar:
        sinav = not_kaydi.sinav
        ders = sinav.ders
        if ders.id not in ders_notlari:
            ders_notlari[ders.id] = {
                'ders': ders,
                'notlar': [],
                'ortalama': 0,
            }
        ders_notlari[ders.id]['notlar'].append(not_kaydi)

    # Ortalamaları hesapla
    for ders_id, veri in ders_notlari.items():
        puanlar = [n.puan for n in veri['notlar']]
        veri['ortalama'] = round(sum(puanlar) / len(puanlar), 2) if puanlar else 0

    # Genel ortalama
    tum_puanlar = [n.puan for n in notlar]
    genel_ortalama = round(sum(tum_puanlar) / len(tum_puanlar), 2) if tum_puanlar else 0

    return render_template('not_defteri/ogrenci_karnesi.html',
                           ogrenci=ogrenci,
                           ders_notlari=ders_notlari,
                           genel_ortalama=genel_ortalama)


@bp.route('/sinif/')
@login_required
@role_required('admin', 'ogretmen')
def sinif_raporu():
    sube_id = request.args.get('sube_id', type=int)

    subeler = Sube.query.join(Sube.sinif).filter(
        Sube.aktif == True
    ).order_by(Sinif.seviye, Sube.ad).all()

    ogrenci_verileri = []
    secili_sube = None

    if sube_id:
        secili_sube = Sube.query.get(sube_id)

        # Şubedeki öğrencileri getir
        kayitlar = OgrenciKayit.query.filter_by(
            sube_id=sube_id, durum='aktif'
        ).all()
        ogrenciler = [k.ogrenci for k in kayitlar]

        if not ogrenciler:
            ogrenciler = Ogrenci.query.filter_by(aktif=True).order_by(
                Ogrenci.ad, Ogrenci.soyad
            ).all()

        for ogr in ogrenciler:
            notlar = OgrenciNot.query.filter_by(ogrenci_id=ogr.id).filter(
                OgrenciNot.puan.isnot(None)
            ).all()
            puanlar = [n.puan for n in notlar]
            ortalama = round(sum(puanlar) / len(puanlar), 2) if puanlar else 0
            sinav_sayisi = len(puanlar)

            ogrenci_verileri.append({
                'ogrenci': ogr,
                'ortalama': ortalama,
                'sinav_sayisi': sinav_sayisi,
            })

        # Ortalamaya göre sırala
        ogrenci_verileri.sort(key=lambda x: x['ortalama'], reverse=True)

    return render_template('not_defteri/sinif_raporu.html',
                           subeler=subeler,
                           sube_id=sube_id,
                           secili_sube=secili_sube,
                           ogrenci_verileri=ogrenci_verileri)
