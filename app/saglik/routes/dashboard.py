from flask import Blueprint, render_template
from flask_login import login_required
from app.utils import role_required
from datetime import datetime, date
from app.extensions import db
from app.models.saglik import SaglikKaydi, RevirKaydi, AsiTakip, SaglikTaramasi

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
@role_required('admin',)
def index():
    today = date.today()

    # Istatistikler
    toplam_kayit = SaglikKaydi.query.count()

    bugunun_revir = RevirKaydi.query.filter(
        db.func.date(RevirKaydi.tarih) == today
    ).count()

    bekleyen_asi = AsiTakip.query.filter(
        AsiTakip.durum.in_(['bekliyor', 'gecikti'])
    ).count()

    yaklasan_tarama = SaglikTaramasi.query.filter(
        SaglikTaramasi.tarama_tarihi >= today
    ).count()

    # Son revir kayitlari
    son_revir = RevirKaydi.query.order_by(
        RevirKaydi.tarih.desc()
    ).limit(5).all()

    # Geciken asilar
    geciken_asilar = AsiTakip.query.filter(
        AsiTakip.durum == 'gecikti'
    ).order_by(AsiTakip.hatirlatma_tarihi).limit(5).all()

    return render_template('saglik/index.html',
                           toplam_kayit=toplam_kayit,
                           bugunun_revir=bugunun_revir,
                           bekleyen_asi=bekleyen_asi,
                           yaklasan_tarama=yaklasan_tarama,
                           son_revir=son_revir,
                           geciken_asilar=geciken_asilar)
