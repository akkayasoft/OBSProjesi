from flask import Blueprint, render_template
from flask_login import login_required
from app.utils import role_required, current_user
from datetime import datetime, timedelta
from app.models.duyurular import Duyuru, Etkinlik, Hatirlatma

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def index():
    now = datetime.utcnow()

    # Son duyurular: sabitlenenler önce, sonra tarihe göre
    duyurular = Duyuru.query.filter_by(aktif=True).order_by(
        Duyuru.sabitlenmis.desc(),
        Duyuru.yayinlanma_tarihi.desc()
    ).limit(5).all()

    # Yaklaşan etkinlikler
    yaklasan_etkinlikler = Etkinlik.query.filter(
        Etkinlik.aktif == True,
        Etkinlik.baslangic_tarihi >= now
    ).order_by(Etkinlik.baslangic_tarihi).limit(5).all()

    # Bekleyen hatırlatmalar
    hatirlatmalar = Hatirlatma.query.filter(
        Hatirlatma.kullanici_id == current_user.id,
        Hatirlatma.tamamlandi == False
    ).order_by(Hatirlatma.tarih).limit(5).all()

    # İstatistikler
    toplam_duyuru = Duyuru.query.filter_by(aktif=True).count()
    toplam_etkinlik = Etkinlik.query.filter(
        Etkinlik.aktif == True,
        Etkinlik.baslangic_tarihi >= now
    ).count()
    bekleyen_hatirlatma = Hatirlatma.query.filter(
        Hatirlatma.kullanici_id == current_user.id,
        Hatirlatma.tamamlandi == False
    ).count()

    return render_template('duyurular/index.html',
                           duyurular=duyurular,
                           yaklasan_etkinlikler=yaklasan_etkinlikler,
                           hatirlatmalar=hatirlatmalar,
                           toplam_duyuru=toplam_duyuru,
                           toplam_etkinlik=toplam_etkinlik,
                           bekleyen_hatirlatma=bekleyen_hatirlatma)
