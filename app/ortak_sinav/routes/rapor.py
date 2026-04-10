from flask import Blueprint, render_template, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.ortak_sinav import OrtakSinav, OrtakSinavSonuc
from app.models.kayit import Sinif, Sube
from app.models.ders_dagitimi import Ders
from sqlalchemy import func

bp = Blueprint('rapor', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def genel():
    sinav_id = request.args.get('sinav_id', '', type=str)
    seviye = request.args.get('seviye', '', type=str)
    ders_id = request.args.get('ders_id', '', type=str)
    donem = request.args.get('donem', '')

    sinav = None
    sube_karsilastirma = []
    genel_istatistik = {}
    puan_dagilimi = {}

    # Sinavlari filtrele
    sinav_query = OrtakSinav.query.filter(OrtakSinav.durum.in_(['degerlendirme', 'tamamlandi']))
    if seviye:
        sinav_query = sinav_query.filter(OrtakSinav.seviye == int(seviye))
    if ders_id:
        sinav_query = sinav_query.filter(OrtakSinav.ders_id == int(ders_id))
    if donem:
        sinav_query = sinav_query.filter(OrtakSinav.donem == donem)

    sinavlar = sinav_query.order_by(OrtakSinav.tarih.desc()).all()

    if sinav_id:
        sinav = OrtakSinav.query.get(int(sinav_id))

        if sinav:
            # Genel istatistikler
            sonuc_query = OrtakSinavSonuc.query.filter_by(ortak_sinav_id=sinav.id)
            toplam_ogrenci = sonuc_query.count()
            ort_puan = db.session.query(
                func.avg(OrtakSinavSonuc.puan)
            ).filter(OrtakSinavSonuc.ortak_sinav_id == sinav.id).scalar()
            en_yuksek = db.session.query(
                func.max(OrtakSinavSonuc.puan)
            ).filter(OrtakSinavSonuc.ortak_sinav_id == sinav.id).scalar()
            en_dusuk = db.session.query(
                func.min(OrtakSinavSonuc.puan)
            ).filter(OrtakSinavSonuc.ortak_sinav_id == sinav.id).scalar()

            gecme_siniri = sinav.toplam_puan * 0.5
            gecen_sayi = sonuc_query.filter(OrtakSinavSonuc.puan >= gecme_siniri).count()

            genel_istatistik = {
                'toplam_ogrenci': toplam_ogrenci,
                'ortalama': round(ort_puan, 2) if ort_puan else 0,
                'en_yuksek': en_yuksek or 0,
                'en_dusuk': en_dusuk or 0,
                'gecen_sayi': gecen_sayi,
                'basari_orani': round((gecen_sayi / toplam_ogrenci * 100), 1) if toplam_ogrenci > 0 else 0,
            }

            # Sube bazli karsilastirma
            sube_sonuclari = db.session.query(
                Sube.id,
                Sube.ad,
                Sinif.ad.label('sinif_ad'),
                func.count(OrtakSinavSonuc.id).label('ogrenci_sayisi'),
                func.avg(OrtakSinavSonuc.puan).label('ortalama'),
                func.max(OrtakSinavSonuc.puan).label('en_yuksek'),
                func.min(OrtakSinavSonuc.puan).label('en_dusuk'),
            ).join(
                OrtakSinavSonuc, OrtakSinavSonuc.sube_id == Sube.id
            ).join(
                Sinif, Sinif.id == Sube.sinif_id
            ).filter(
                OrtakSinavSonuc.ortak_sinav_id == sinav.id
            ).group_by(Sube.id, Sube.ad, Sinif.ad).all()

            sube_labels = []
            sube_ortalamalar = []
            for s in sube_sonuclari:
                sube_adi = f"{s.sinif_ad} - {s.ad}"
                sube_labels.append(sube_adi)
                sube_ortalamalar.append(round(s.ortalama, 2) if s.ortalama else 0)
                sube_karsilastirma.append({
                    'sube_id': s.id,
                    'sube_ad': sube_adi,
                    'ogrenci_sayisi': s.ogrenci_sayisi,
                    'ortalama': round(s.ortalama, 2) if s.ortalama else 0,
                    'en_yuksek': s.en_yuksek or 0,
                    'en_dusuk': s.en_dusuk or 0,
                })

            # Puan dagilimi (0-25, 25-50, 50-75, 75-100)
            toplam_p = sinav.toplam_puan
            araliklar = [
                (0, toplam_p * 0.25),
                (toplam_p * 0.25, toplam_p * 0.50),
                (toplam_p * 0.50, toplam_p * 0.75),
                (toplam_p * 0.75, toplam_p + 1),
            ]
            aralik_labels = ['0-25%', '25-50%', '50-75%', '75-100%']
            aralik_values = []
            for alt, ust in araliklar:
                sayi = OrtakSinavSonuc.query.filter(
                    OrtakSinavSonuc.ortak_sinav_id == sinav.id,
                    OrtakSinavSonuc.puan >= alt,
                    OrtakSinavSonuc.puan < ust
                ).count()
                aralik_values.append(sayi)

            puan_dagilimi = {
                'labels': aralik_labels,
                'values': aralik_values,
                'sube_labels': sube_labels,
                'sube_ortalamalar': sube_ortalamalar,
            }

    dersler = Ders.query.filter_by(aktif=True).order_by(Ders.ad).all()

    return render_template('ortak_sinav/rapor.html',
                           sinavlar=sinavlar,
                           dersler=dersler,
                           sinav=sinav,
                           sinav_id=sinav_id,
                           seviye=seviye,
                           ders_id=ders_id,
                           donem=donem,
                           genel_istatistik=genel_istatistik,
                           sube_karsilastirma=sube_karsilastirma,
                           puan_dagilimi=puan_dagilimi)
