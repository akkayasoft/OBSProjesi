from flask import Blueprint, render_template, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.etut import Etut, EtutKatilim
from app.models.muhasebe import Ogrenci

bp = Blueprint('rapor', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def index():
    # Etut bazli rapor
    etut_id = request.args.get('etut_id', 0, type=int)
    ogrenci_id = request.args.get('ogrenci_id', 0, type=int)

    etutler = Etut.query.filter_by(aktif=True).order_by(Etut.ad).all()
    ogrenciler = Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad).all()

    etut_rapor = None
    ogrenci_rapor = None

    if etut_id:
        etut = Etut.query.get(etut_id)
        if etut:
            # Ogrenci bazli katilim istatistikleri
            ogrenci_stats = db.session.query(
                EtutKatilim.ogrenci_id,
                db.func.count(EtutKatilim.id).label('toplam_ders'),
                db.func.sum(db.case((EtutKatilim.katildi.is_(True), 1), else_=0)).label('katilim'),
            ).filter(
                EtutKatilim.etut_id == etut_id
            ).group_by(
                EtutKatilim.ogrenci_id
            ).all()

            etut_rapor = {
                'etut': etut,
                'ogrenci_stats': [],
            }

            for stat in ogrenci_stats:
                ogrenci = Ogrenci.query.get(stat.ogrenci_id)
                if ogrenci:
                    toplam = stat.toplam_ders or 0
                    katilim = stat.katilim or 0
                    oran = round((katilim / toplam * 100), 1) if toplam > 0 else 0
                    etut_rapor['ogrenci_stats'].append({
                        'ogrenci': ogrenci,
                        'toplam_ders': toplam,
                        'katilim': katilim,
                        'devamsizlik': toplam - katilim,
                        'oran': oran,
                    })

            # Orana gore sirala (azalan)
            etut_rapor['ogrenci_stats'].sort(key=lambda x: x['oran'], reverse=True)

    if ogrenci_id:
        ogrenci = Ogrenci.query.get(ogrenci_id)
        if ogrenci:
            # Etut bazli katilim istatistikleri
            etut_stats = db.session.query(
                EtutKatilim.etut_id,
                db.func.count(EtutKatilim.id).label('toplam_ders'),
                db.func.sum(db.case((EtutKatilim.katildi.is_(True), 1), else_=0)).label('katilim'),
            ).filter(
                EtutKatilim.ogrenci_id == ogrenci_id
            ).group_by(
                EtutKatilim.etut_id
            ).all()

            ogrenci_rapor = {
                'ogrenci': ogrenci,
                'etut_stats': [],
            }

            for stat in etut_stats:
                etut = Etut.query.get(stat.etut_id)
                if etut:
                    toplam = stat.toplam_ders or 0
                    katilim = stat.katilim or 0
                    oran = round((katilim / toplam * 100), 1) if toplam > 0 else 0
                    ogrenci_rapor['etut_stats'].append({
                        'etut': etut,
                        'toplam_ders': toplam,
                        'katilim': katilim,
                        'devamsizlik': toplam - katilim,
                        'oran': oran,
                    })

    # Genel istatistikler
    toplam_etut = Etut.query.filter_by(aktif=True).count()
    toplam_katilim = EtutKatilim.query.count()
    toplam_katilan = EtutKatilim.query.filter_by(katildi=True).count()
    genel_oran = round((toplam_katilan / toplam_katilim * 100), 1) if toplam_katilim > 0 else 0

    return render_template('etut/rapor.html',
                           etutler=etutler,
                           ogrenciler=ogrenciler,
                           secili_etut_id=etut_id,
                           secili_ogrenci_id=ogrenci_id,
                           etut_rapor=etut_rapor,
                           ogrenci_rapor=ogrenci_rapor,
                           toplam_etut=toplam_etut,
                           toplam_katilim=toplam_katilim,
                           toplam_katilan=toplam_katilan,
                           genel_oran=genel_oran)
