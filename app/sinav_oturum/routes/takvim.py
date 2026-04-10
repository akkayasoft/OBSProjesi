from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app.utils import role_required
from app.models.sinav_oturum import SinavOturum
from datetime import datetime

bp = Blueprint('takvim', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def goruntule():
    return render_template('sinav_oturum/takvim.html')


@bp.route('/veriler')
@login_required
@role_required('admin', 'ogretmen')
def veriler():
    """Takvim icin JSON veri endpoint'i."""
    baslangic = request.args.get('start', '')
    bitis = request.args.get('end', '')

    query = SinavOturum.query

    if baslangic:
        try:
            b_tarih = datetime.strptime(baslangic[:10], '%Y-%m-%d').date()
            query = query.filter(SinavOturum.tarih >= b_tarih)
        except ValueError:
            pass
    if bitis:
        try:
            bt_tarih = datetime.strptime(bitis[:10], '%Y-%m-%d').date()
            query = query.filter(SinavOturum.tarih <= bt_tarih)
        except ValueError:
            pass

    oturumlar = query.order_by(SinavOturum.tarih, SinavOturum.baslangic_saati).all()

    renk_map = {
        'planlanmis': '#6c757d',
        'devam_ediyor': '#ffc107',
        'tamamlandi': '#198754',
        'iptal': '#dc3545',
    }

    events = []
    for o in oturumlar:
        events.append({
            'id': o.id,
            'title': f'{o.ad} ({o.sinav_turu_str})',
            'start': f'{o.tarih.isoformat()}T{o.baslangic_saati.strftime("%H:%M")}',
            'end': f'{o.tarih.isoformat()}T{o.bitis_saati.strftime("%H:%M")}',
            'color': renk_map.get(o.durum, '#6c757d'),
            'url': f'/sinav_oturum/oturum/{o.id}',
            'extendedProps': {
                'sinif': o.sinif.ad if o.sinif else '',
                'ders': o.ders.ad if o.ders else '',
                'ogretmen': o.ogretmen.tam_ad if o.ogretmen else '',
                'durum': o.durum_str,
                'derslik': o.derslik or '',
            }
        })

    return jsonify(events)
