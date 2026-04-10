from flask import Blueprint, render_template
from flask_login import login_required
from app.utils import role_required
from app.models.ayarlar import SistemAyar

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
@role_required('admin')
def index():
    kategoriler = ['genel', 'akademik', 'muhasebe', 'iletisim', 'guvenlik']
    ayarlar = {}
    for kat in kategoriler:
        ayarlar[kat] = SistemAyar.query.filter_by(kategori=kat).order_by(
            SistemAyar.id.asc()
        ).all()

    return render_template('ayarlar/index.html',
                           ayarlar=ayarlar,
                           aktif_tab='genel')
