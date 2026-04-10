from flask import Blueprint, render_template, flash
from flask_login import login_required, current_user
from app.utils import role_required
from app.models.muhasebe import Ogrenci
from app.models.devamsizlik import Devamsizlik
from app.extensions import db
from datetime import date

bp = Blueprint('devamsizlik_portal', __name__)


def get_current_ogrenci():
    if current_user.rol == 'veli':
        return Ogrenci.query.filter_by(soyad=current_user.soyad, aktif=True).first()
    return Ogrenci.query.filter_by(ad=current_user.ad, soyad=current_user.soyad, aktif=True).first()


@bp.route('/devamsizlik/')
@login_required
@role_required('ogrenci', 'veli', 'admin')
def index():
    ogrenci = get_current_ogrenci()
    if not ogrenci:
        flash('Ogrenci kaydiniz bulunamadi.', 'warning')
        return render_template('ogrenci_portal/devamsizlik.html',
                               ogrenci=None, kayitlar=[], istatistik={})

    # Tum devamsizlik kayitlari
    kayitlar = Devamsizlik.query.filter_by(
        ogrenci_id=ogrenci.id
    ).order_by(Devamsizlik.tarih.desc(), Devamsizlik.ders_saati.asc()).all()

    # Istatistikler
    toplam_devamsiz = 0
    toplam_gec = 0
    toplam_izinli = 0
    toplam_raporlu = 0
    aylik = {}

    for k in kayitlar:
        if k.durum == 'devamsiz':
            toplam_devamsiz += 1
        elif k.durum == 'gec':
            toplam_gec += 1
        elif k.durum == 'izinli':
            toplam_izinli += 1
        elif k.durum == 'raporlu':
            toplam_raporlu += 1

        ay_key = k.tarih.strftime('%Y-%m')
        ay_label = k.tarih.strftime('%m/%Y')
        if ay_key not in aylik:
            aylik[ay_key] = {'label': ay_label, 'sayi': 0}
        aylik[ay_key]['sayi'] += 1

    # Aylari sirala
    aylik_sirali = [aylik[k] for k in sorted(aylik.keys())]

    istatistik = {
        'toplam_devamsiz': toplam_devamsiz,
        'toplam_gec': toplam_gec,
        'toplam_izinli': toplam_izinli,
        'toplam_raporlu': toplam_raporlu,
        'toplam': len(kayitlar),
        'aylik': aylik_sirali,
    }

    return render_template('ogrenci_portal/devamsizlik.html',
                           ogrenci=ogrenci, kayitlar=kayitlar, istatistik=istatistik)
