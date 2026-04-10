from flask import Blueprint, render_template
from flask_login import login_required
from app.utils import role_required, current_user
from app.models.iletisim import Mesaj, TopluMesaj, MesajSablonu, IletisimDefteri

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def index():
    # Okunmamış mesaj sayısı
    okunmamis_mesaj = Mesaj.query.filter(
        Mesaj.alici_id == current_user.id,
        Mesaj.okundu == False,
        Mesaj.silindi_alici == False
    ).count()

    # Son gelen mesajlar
    son_mesajlar = Mesaj.query.filter(
        Mesaj.alici_id == current_user.id,
        Mesaj.silindi_alici == False
    ).order_by(Mesaj.created_at.desc()).limit(5).all()

    # Son toplu mesajlar
    son_toplu_mesajlar = TopluMesaj.query.order_by(
        TopluMesaj.created_at.desc()
    ).limit(5).all()

    # İstatistikler
    toplam_toplu_mesaj = TopluMesaj.query.count()
    sablon_sayisi = MesajSablonu.query.filter_by(aktif=True).count()
    rehber_sayisi = IletisimDefteri.query.filter_by(aktif=True).count()

    return render_template('iletisim/index.html',
                           okunmamis_mesaj=okunmamis_mesaj,
                           son_mesajlar=son_mesajlar,
                           son_toplu_mesajlar=son_toplu_mesajlar,
                           toplam_toplu_mesaj=toplam_toplu_mesaj,
                           sablon_sayisi=sablon_sayisi,
                           rehber_sayisi=rehber_sayisi)
