from flask import Blueprint, render_template
from flask_login import login_required
from app.utils import role_required
from app.models.kurum import Kurum, OgretimYili, Tatil, Derslik
from app.extensions import db
from datetime import date

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
@role_required('admin')
def index():
    kurum = Kurum.query.first()
    aktif_ogretim_yili = OgretimYili.query.filter_by(aktif=True).first()

    # Yaklasan tatiller
    bugun = date.today()
    yaklasan_tatiller = Tatil.query.filter(
        Tatil.baslangic_tarihi >= bugun
    ).order_by(Tatil.baslangic_tarihi.asc()).limit(5).all()

    # Derslik istatistikleri
    toplam_derslik = Derslik.query.count()
    aktif_derslik = Derslik.query.filter_by(aktif=True).count()
    toplam_kapasite = db.session.query(
        db.func.sum(Derslik.kapasite)
    ).filter(Derslik.aktif == True).scalar() or 0  # noqa: E712

    # Tur dagilimi
    tur_dagilimi = db.session.query(
        Derslik.tur, db.func.count(Derslik.id)
    ).filter(Derslik.aktif == True).group_by(Derslik.tur).all()  # noqa: E712

    return render_template('kurum/index.html',
                           kurum=kurum,
                           aktif_ogretim_yili=aktif_ogretim_yili,
                           yaklasan_tatiller=yaklasan_tatiller,
                           toplam_derslik=toplam_derslik,
                           aktif_derslik=aktif_derslik,
                           toplam_kapasite=toplam_kapasite,
                           tur_dagilimi=tur_dagilimi)
