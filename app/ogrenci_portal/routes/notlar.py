from flask import Blueprint, render_template, flash
from flask_login import login_required, current_user
from app.utils import role_required
from app.models.muhasebe import Ogrenci
from app.models.not_defteri import OgrenciNot, Sinav
from app.models.ders_dagitimi import Ders
from app.extensions import db

bp = Blueprint('notlar', __name__)


def get_current_ogrenci():
    if current_user.rol == 'veli':
        return Ogrenci.query.filter_by(soyad=current_user.soyad, aktif=True).first()
    return Ogrenci.query.filter_by(ad=current_user.ad, soyad=current_user.soyad, aktif=True).first()


@bp.route('/notlar/')
@login_required
@role_required('ogrenci', 'veli', 'admin')
def index():
    ogrenci = get_current_ogrenci()
    if not ogrenci:
        flash('Ogrenci kaydiniz bulunamadi.', 'warning')
        return render_template('ogrenci_portal/notlar.html',
                               ogrenci=None, dersler=[])

    # Ogrencinin tum notlarini getir
    notlar = OgrenciNot.query.filter_by(ogrenci_id=ogrenci.id).all()

    # Ders bazinda grupla
    ders_notlari = {}
    for n in notlar:
        sinav = n.sinav
        ders = sinav.ders
        if ders.id not in ders_notlari:
            ders_notlari[ders.id] = {
                'ders': ders,
                'notlar': [],
                'toplam': 0,
                'sayi': 0,
            }
        ders_notlari[ders.id]['notlar'].append({
            'sinav_ad': sinav.ad,
            'sinav_turu': sinav.sinav_turu.ad if sinav.sinav_turu else '',
            'tarih': sinav.tarih,
            'puan': n.puan,
            'harf_notu': n.harf_notu,
        })
        if n.puan is not None:
            ders_notlari[ders.id]['toplam'] += n.puan
            ders_notlari[ders.id]['sayi'] += 1

    # Ortalama hesapla
    dersler = []
    for ders_id, data in ders_notlari.items():
        ortalama = round(data['toplam'] / data['sayi'], 1) if data['sayi'] > 0 else 0
        dersler.append({
            'ders': data['ders'],
            'notlar': sorted(data['notlar'], key=lambda x: x['tarih'] if x['tarih'] else db.func.now()),
            'ortalama': ortalama,
        })

    dersler.sort(key=lambda x: x['ders'].ad)

    return render_template('ogrenci_portal/notlar.html',
                           ogrenci=ogrenci, dersler=dersler)
