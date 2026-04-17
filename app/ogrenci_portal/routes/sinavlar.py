from flask import Blueprint, render_template, flash
from flask_login import login_required, current_user
from app.utils import role_required
from app.models.muhasebe import Ogrenci
from app.models.kayit import OgrenciKayit
from app.models.online_sinav import OnlineSinav, SinavKatilim
from app.ogrenci_portal.helpers import get_current_ogrenci
from app.extensions import db
from datetime import datetime

bp = Blueprint('sinavlar', __name__)


@bp.route('/sinavlar/')
@login_required
@role_required('ogrenci', 'veli', 'admin')
def index():
    ogrenci = get_current_ogrenci()
    if not ogrenci:
        flash('Ogrenci kaydiniz bulunamadi.', 'warning')
        return render_template('ogrenci_portal/sinavlar.html',
                               ogrenci=None, yaklasan=[], gecmis=[])

    # Ogrencinin subesini bul
    kayit = OgrenciKayit.query.filter_by(
        ogrenci_id=ogrenci.id, durum='aktif'
    ).first()

    now = datetime.utcnow()
    yaklasan = []
    gecmis = []

    if kayit:
        sinavlar = OnlineSinav.query.filter(
            OnlineSinav.aktif == True,  # noqa: E712
            db.or_(
                OnlineSinav.sube_id == kayit.sube_id,
                OnlineSinav.sube_id.is_(None)
            )
        ).order_by(OnlineSinav.baslangic_zamani.desc()).all()

        for sinav in sinavlar:
            # Katilim durumunu kontrol et
            katilim = SinavKatilim.query.filter_by(
                sinav_id=sinav.id, ogrenci_id=ogrenci.id
            ).first()

            sinav_data = {
                'sinav': sinav,
                'katilim': katilim,
            }

            if sinav.bitis_zamani > now:
                yaklasan.append(sinav_data)
            else:
                gecmis.append(sinav_data)

    return render_template('ogrenci_portal/sinavlar.html',
                           ogrenci=ogrenci, yaklasan=yaklasan, gecmis=gecmis)
