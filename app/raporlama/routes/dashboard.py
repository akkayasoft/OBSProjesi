from flask import Blueprint, render_template
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.muhasebe import Ogrenci, Personel
from app.models.kayit import Sinif, Sube
from app.models.user import User

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
@role_required('admin')
def index():
    toplam_ogrenci = Ogrenci.query.filter_by(aktif=True).count()
    toplam_personel = Personel.query.filter_by(aktif=True).count()
    toplam_sinif = Sinif.query.filter_by(aktif=True).count()
    toplam_kullanici = User.query.count()

    # Rol dagilimi
    rol_dagilim = db.session.query(
        User.rol, db.func.count(User.id)
    ).group_by(User.rol).all()
    rol_labels = [r[0] for r in rol_dagilim]
    rol_values = [r[1] for r in rol_dagilim]

    # Sinif bazinda ogrenci dagilimi (sinif string alanı üzerinden)
    sinif_dagilim = db.session.query(
        Ogrenci.sinif, db.func.count(Ogrenci.id)
    ).filter(Ogrenci.aktif == True).group_by(Ogrenci.sinif).all()
    sinif_labels = [s[0] or 'Belirtilmemiş' for s in sinif_dagilim]
    sinif_values = [s[1] for s in sinif_dagilim]

    return render_template('raporlama/index.html',
                           toplam_ogrenci=toplam_ogrenci,
                           toplam_personel=toplam_personel,
                           toplam_sinif=toplam_sinif,
                           toplam_kullanici=toplam_kullanici,
                           rol_labels=rol_labels, rol_values=rol_values,
                           sinif_labels=sinif_labels, sinif_values=sinif_values)
