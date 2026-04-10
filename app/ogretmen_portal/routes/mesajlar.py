from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.utils import role_required
from app.models.iletisim import Mesaj

bp = Blueprint('mesajlar', __name__)


@bp.route('/mesajlar/')
@login_required
@role_required('ogretmen', 'admin')
def index():
    mesajlar = Mesaj.query.filter_by(
        alici_id=current_user.id, silindi_alici=False
    ).order_by(Mesaj.created_at.desc()).all()

    okunmamis_sayisi = Mesaj.query.filter_by(
        alici_id=current_user.id, okundu=False, silindi_alici=False
    ).count()

    return render_template('ogretmen_portal/mesajlar.html',
                           mesajlar=mesajlar,
                           okunmamis_sayisi=okunmamis_sayisi)
