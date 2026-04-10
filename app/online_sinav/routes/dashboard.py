from flask import Blueprint, render_template
from flask_login import login_required
from app.utils import role_required
from datetime import datetime
from app.models.online_sinav import OnlineSinav, SinavKatilim

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def index():
    now = datetime.utcnow()

    # Istatistikler
    toplam_sinav = OnlineSinav.query.count()
    aktif_sinav = OnlineSinav.query.filter(
        OnlineSinav.aktif == True,
        OnlineSinav.baslangic_zamani <= now,
        OnlineSinav.bitis_zamani >= now
    ).count()
    tamamlanan = SinavKatilim.query.filter(
        SinavKatilim.durum.in_(['tamamlandi', 'suresi_doldu'])
    ).count()

    # Ortalama basari
    tamamlanan_katilimlar = SinavKatilim.query.filter(
        SinavKatilim.durum.in_(['tamamlandi', 'suresi_doldu']),
        SinavKatilim.toplam_puan.isnot(None)
    ).all()
    ortalama_basari = 0
    if tamamlanan_katilimlar:
        ortalama_basari = round(
            sum(k.toplam_puan for k in tamamlanan_katilimlar) / len(tamamlanan_katilimlar), 1
        )

    # Yaklasan sinavlar
    yaklasan_sinavlar = OnlineSinav.query.filter(
        OnlineSinav.aktif == True,
        OnlineSinav.baslangic_zamani >= now
    ).order_by(OnlineSinav.baslangic_zamani).limit(5).all()

    # Son sonuclar
    son_katilimlar = SinavKatilim.query.filter(
        SinavKatilim.durum.in_(['tamamlandi', 'suresi_doldu'])
    ).order_by(SinavKatilim.bitirme_zamani.desc()).limit(10).all()

    return render_template('online_sinav/index.html',
                           toplam_sinav=toplam_sinav,
                           aktif_sinav=aktif_sinav,
                           tamamlanan=tamamlanan,
                           ortalama_basari=ortalama_basari,
                           yaklasan_sinavlar=yaklasan_sinavlar,
                           son_katilimlar=son_katilimlar)
