from datetime import date
from flask import Blueprint, render_template
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.not_defteri import OdevTakip, OdevTeslim

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def index():
    bugun = date.today()

    toplam_odev = OdevTakip.query.filter_by(aktif=True).count()

    # Bekleyen teslimler (teslim edilmedi + aktif odevler)
    bekleyen_teslim = db.session.query(OdevTeslim).join(OdevTakip).filter(
        OdevTakip.aktif == True,  # noqa: E712
        OdevTeslim.durum == 'teslim_edilmedi'
    ).count()

    # Suresi gecen odevler
    geciken_odev = OdevTakip.query.filter(
        OdevTakip.aktif == True,  # noqa: E712
        OdevTakip.son_teslim_tarihi < bugun
    ).count()

    # Tamamlanma orani
    toplam_teslim = OdevTeslim.query.join(OdevTakip).filter(
        OdevTakip.aktif == True  # noqa: E712
    ).count()
    teslim_edilen = OdevTeslim.query.join(OdevTakip).filter(
        OdevTakip.aktif == True,  # noqa: E712
        OdevTeslim.durum == 'teslim_edildi'
    ).count()
    tamamlanma_orani = round(teslim_edilen / toplam_teslim * 100, 1) if toplam_teslim > 0 else 0

    # Son eklenen odevler
    son_odevler = OdevTakip.query.filter_by(aktif=True).order_by(
        OdevTakip.created_at.desc()
    ).limit(5).all()

    # Suresi yaklasmis odevler (yaklasan 7 gun)
    from datetime import timedelta
    yaklasan_tarih = bugun + timedelta(days=7)
    yaklasan_odevler = OdevTakip.query.filter(
        OdevTakip.aktif == True,  # noqa: E712
        OdevTakip.son_teslim_tarihi >= bugun,
        OdevTakip.son_teslim_tarihi <= yaklasan_tarih
    ).order_by(OdevTakip.son_teslim_tarihi).all()

    # Ders bazli odev sayilari (grafik icin)
    ders_istatistik = db.session.query(
        db.func.count(OdevTakip.id)
    ).filter(
        OdevTakip.aktif == True  # noqa: E712
    ).scalar() or 0

    return render_template('odev_takip/index.html',
                           toplam_odev=toplam_odev,
                           bekleyen_teslim=bekleyen_teslim,
                           geciken_odev=geciken_odev,
                           tamamlanma_orani=tamamlanma_orani,
                           son_odevler=son_odevler,
                           yaklasan_odevler=yaklasan_odevler)
