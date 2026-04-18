"""Ogrenci/veli portali karne goruntuleme.

Sadece onaylanmis (onaylandi/basildi) karneler gosterilir; taslak karneler
ogrenciye acik degildir.
"""
from flask import Blueprint, render_template, flash, abort
from flask_login import login_required

from app.utils import role_required
from app.models.karne import Karne
from app.ogrenci_portal.helpers import get_current_ogrenci


bp = Blueprint('karne_portal', __name__, url_prefix='/karne')


@bp.route('/')
@login_required
@role_required('ogrenci', 'veli', 'admin')
def index():
    """Ogrencinin onaylanmis karneleri."""
    ogrenci = get_current_ogrenci()
    if not ogrenci:
        flash('Ogrenci kaydiniz bulunamadi.', 'warning')
        return render_template('ogrenci_portal/karne_liste.html',
                               ogrenci=None, karneler=[])

    karneler = (
        Karne.query
        .filter(Karne.ogrenci_id == ogrenci.id,
                Karne.durum.in_(['onaylandi', 'basildi']))
        .order_by(Karne.ogretim_yili.desc(), Karne.donem.desc())
        .all()
    )

    return render_template(
        'ogrenci_portal/karne_liste.html',
        ogrenci=ogrenci,
        karneler=karneler,
    )


@bp.route('/<int:karne_id>')
@login_required
@role_required('ogrenci', 'veli', 'admin')
def detay(karne_id):
    """Tek bir karne detayi."""
    ogrenci = get_current_ogrenci()
    if not ogrenci:
        flash('Ogrenci kaydiniz bulunamadi.', 'warning')
        abort(404)

    karne = Karne.query.get_or_404(karne_id)

    # Guvenlik: sadece kendi karnesi ve onaylanmis olmali
    if karne.ogrenci_id != ogrenci.id:
        abort(403)
    if karne.durum not in ('onaylandi', 'basildi'):
        flash('Bu karne henuz onaylanmamis, goruntulenemez.', 'warning')
        abort(403)

    ders_notlari = karne.ders_notlari.order_by().all()

    return render_template(
        'ogrenci_portal/karne_detay.html',
        ogrenci=ogrenci,
        karne=karne,
        ders_notlari=ders_notlari,
    )
