from flask import Blueprint, render_template
from flask_login import login_required
from app.utils import role_required
from app.models.ders_dagitimi import Ders, DersProgrami, OgretmenDersAtama

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def index():
    toplam_ders = Ders.query.filter_by(aktif=True).count()
    toplam_program = DersProgrami.query.filter_by(aktif=True).count()
    toplam_atama = OgretmenDersAtama.query.filter_by(aktif=True).count()

    # Kategoriye göre ders dağılımı
    from app.extensions import db
    kategori_query = db.session.query(
        Ders.kategori,
        db.func.count(Ders.id)
    ).filter(Ders.aktif == True).group_by(Ders.kategori).all()

    kategori_labels = [k[0] for k in kategori_query]
    kategori_values = [k[1] for k in kategori_query]

    # Son eklenen dersler
    son_dersler = Ders.query.filter_by(aktif=True).order_by(Ders.created_at.desc()).limit(5).all()

    return render_template('ders_dagitimi/index.html',
                           toplam_ders=toplam_ders,
                           toplam_program=toplam_program,
                           toplam_atama=toplam_atama,
                           kategori_labels=kategori_labels,
                           kategori_values=kategori_values,
                           son_dersler=son_dersler)
