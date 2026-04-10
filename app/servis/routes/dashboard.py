from flask import Blueprint, render_template
from flask_login import login_required
from app.utils import role_required
from app.models.servis import Guzergah, Arac, ServisKayit
from app.extensions import db

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
@role_required('admin')
def index():
    toplam_guzergah = Guzergah.query.filter_by(aktif=True).count()
    toplam_arac = Arac.query.filter_by(aktif=True).count()
    toplam_kayitli = ServisKayit.query.filter_by(durum='aktif').count()

    # Doluluk orani hesapla
    toplam_kapasite = db.session.query(
        db.func.sum(Arac.kapasite)
    ).filter_by(aktif=True).scalar() or 0
    doluluk_orani = round((toplam_kayitli / toplam_kapasite * 100), 1) if toplam_kapasite > 0 else 0

    # Guzergah bazinda ogrenci dagilimi
    guzergah_dagilim = db.session.query(
        Guzergah.ad, db.func.count(ServisKayit.id)
    ).join(ServisKayit, Guzergah.id == ServisKayit.guzergah_id).filter(
        ServisKayit.durum == 'aktif'
    ).group_by(Guzergah.ad).all()

    guzergah_labels = [g[0] for g in guzergah_dagilim]
    guzergah_values = [g[1] for g in guzergah_dagilim]

    # Son eklenen guzergahlar
    son_guzergahlar = Guzergah.query.filter_by(aktif=True).order_by(
        Guzergah.created_at.desc()
    ).limit(5).all()

    return render_template('servis/index.html',
                           toplam_guzergah=toplam_guzergah,
                           toplam_arac=toplam_arac,
                           toplam_kayitli=toplam_kayitli,
                           doluluk_orani=doluluk_orani,
                           guzergah_labels=guzergah_labels,
                           guzergah_values=guzergah_values,
                           son_guzergahlar=son_guzergahlar)
