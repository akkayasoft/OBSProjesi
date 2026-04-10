from flask import Blueprint, render_template
from flask_login import login_required
from app.utils import role_required
from app.models.not_defteri import Sinav, OgrenciNot, OdevTakip, OdevTeslim

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def index():
    toplam_sinav = Sinav.query.filter_by(aktif=True).count()
    toplam_odev = OdevTakip.query.filter_by(aktif=True).count()

    # Ortalama puan
    from app.extensions import db
    ort_result = db.session.query(db.func.avg(OgrenciNot.puan)).filter(
        OgrenciNot.puan.isnot(None)
    ).scalar()
    ortalama_puan = round(ort_result, 1) if ort_result else 0

    # Teslim oranı
    toplam_teslim = OdevTeslim.query.count()
    teslim_edilen = OdevTeslim.query.filter_by(durum='teslim_edildi').count()
    teslim_orani = round(teslim_edilen / toplam_teslim * 100, 1) if toplam_teslim > 0 else 0

    # Son sınavlar
    son_sinavlar = Sinav.query.filter_by(aktif=True).order_by(
        Sinav.tarih.desc()
    ).limit(5).all()

    return render_template('not_defteri/index.html',
                           toplam_sinav=toplam_sinav,
                           ortalama_puan=ortalama_puan,
                           toplam_odev=toplam_odev,
                           teslim_orani=teslim_orani,
                           son_sinavlar=son_sinavlar)
