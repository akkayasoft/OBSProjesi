from flask import Blueprint, render_template
from flask_login import login_required
from app.utils import role_required
from app.models.kulupler import Kulup, KulupUyelik, KulupEtkinlik
from app.extensions import db

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def index():
    toplam_kulup = Kulup.query.filter_by(aktif=True).count()
    toplam_uye = KulupUyelik.query.filter_by(durum='aktif').count()
    aktif_etkinlik = KulupEtkinlik.query.filter_by(durum='planlandi').count()

    # Kategori dagilimi
    kategoriler = db.session.query(
        Kulup.kategori, db.func.count(Kulup.id)
    ).filter_by(aktif=True).group_by(Kulup.kategori).all()

    kategori_labels = []
    kategori_values = []
    for kat, sayi in kategoriler:
        kategori_map = {
            'spor': 'Spor', 'sanat': 'Sanat', 'bilim': 'Bilim',
            'sosyal': 'Sosyal', 'kultur': 'Kultur', 'diger': 'Diger',
        }
        kategori_labels.append(kategori_map.get(kat, kat))
        kategori_values.append(sayi)

    # Son eklenen kulupler
    son_kulupler = Kulup.query.filter_by(aktif=True).order_by(
        Kulup.created_at.desc()
    ).limit(5).all()

    # Yaklasan etkinlikler
    from datetime import datetime
    yaklasan_etkinlikler = KulupEtkinlik.query.filter(
        KulupEtkinlik.durum == 'planlandi',
        KulupEtkinlik.tarih >= datetime.utcnow()
    ).order_by(KulupEtkinlik.tarih).limit(5).all()

    return render_template('kulupler/index.html',
                           toplam_kulup=toplam_kulup,
                           toplam_uye=toplam_uye,
                           aktif_etkinlik=aktif_etkinlik,
                           kategori_labels=kategori_labels,
                           kategori_values=kategori_values,
                           son_kulupler=son_kulupler,
                           yaklasan_etkinlikler=yaklasan_etkinlikler)
