from flask import Blueprint, render_template, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.muhasebe import Ogrenci

bp = Blueprint('ogrenci_rapor', __name__)


@bp.route('/')
@login_required
@role_required('admin')
def index():
    # Cinsiyet dagilimi
    cinsiyet = db.session.query(
        Ogrenci.cinsiyet, db.func.count(Ogrenci.id)
    ).filter(Ogrenci.aktif == True).group_by(Ogrenci.cinsiyet).all()

    # Sinif bazinda ogrenci sayilari
    sinif_dagilim = db.session.query(
        Ogrenci.sinif, db.func.count(Ogrenci.id)
    ).filter(Ogrenci.aktif == True).group_by(Ogrenci.sinif).all()

    return render_template('raporlama/ogrenci_rapor.html',
                           cinsiyet=cinsiyet,
                           sinif_dagilim=sinif_dagilim)
