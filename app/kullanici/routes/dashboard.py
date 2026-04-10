from flask import Blueprint, render_template
from flask_login import login_required
from app.utils import role_required
from app.models.user import User
from app.extensions import db

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
@role_required('admin')
def index():
    toplam_kullanici = User.query.count()
    aktif_kullanici = User.query.filter_by(aktif=True).count()
    pasif_kullanici = User.query.filter_by(aktif=False).count()

    # Rol dagilimi
    rol_dagilimi = db.session.query(
        User.rol, db.func.count(User.id)
    ).group_by(User.rol).all()

    rol_labels = []
    rol_values = []
    rol_map = {
        'admin': 'Yonetici',
        'ogretmen': 'Ogretmen',
        'veli': 'Veli',
        'ogrenci': 'Ogrenci',
        'muhasebeci': 'Muhasebeci',
    }
    for rol, sayi in rol_dagilimi:
        rol_labels.append(rol_map.get(rol, rol))
        rol_values.append(sayi)

    # Son eklenen kullanicilar
    son_kullanicilar = User.query.order_by(
        User.olusturma_tarihi.desc()
    ).limit(5).all()

    return render_template('kullanici/index.html',
                           toplam_kullanici=toplam_kullanici,
                           aktif_kullanici=aktif_kullanici,
                           pasif_kullanici=pasif_kullanici,
                           rol_labels=rol_labels,
                           rol_values=rol_values,
                           son_kullanicilar=son_kullanicilar)
