"""Deneme sinavi raporlari: sinav bazli siralama, sube ortalamasi vs."""
from flask import Blueprint, render_template, abort
from flask_login import login_required
from sqlalchemy import func

from app.utils import role_required
from app.extensions import db
from app.models.deneme_sinavi import (DenemeSinavi, DenemeDersi,
                                      DenemeKatilim, DenemeDersSonucu)
from app.models.kayit import Sube


bp = Blueprint('rapor', __name__, url_prefix='/rapor')


@bp.route('/<int:sinav_id>')
@login_required
@role_required('admin', 'ogretmen')
def sinav_raporu(sinav_id):
    """Bir sinavin genel raporu: siralama, ders ortalamalari, sube ortalamalari."""
    sinav = DenemeSinavi.query.get_or_404(sinav_id)
    dersler = sinav.dersler.all()

    # Tum katilimcilar, puana gore sirali
    katilimlar = (DenemeKatilim.query
                  .filter_by(deneme_sinavi_id=sinav.id, katildi=True)
                  .order_by(DenemeKatilim.toplam_puan.desc().nulls_last())
                  .all())

    # Ders bazli ortalama netler
    ders_ortalamalari = {}
    for ders in dersler:
        ort = db.session.query(func.avg(DenemeDersSonucu.net)).join(
            DenemeKatilim, DenemeKatilim.id == DenemeDersSonucu.katilim_id
        ).filter(
            DenemeKatilim.deneme_sinavi_id == sinav.id,
            DenemeDersSonucu.deneme_dersi_id == ders.id,
        ).scalar()
        ders_ortalamalari[ders.id] = round(ort, 2) if ort else 0.0

    # Sube ortalamalari
    sube_ozetleri = []
    sube_ids = {k.sube_id for k in katilimlar if k.sube_id}
    for sid in sube_ids:
        sube = Sube.query.get(sid)
        if not sube:
            continue
        k_sayi = sum(1 for k in katilimlar if k.sube_id == sid)
        ort_net = sum((k.toplam_net or 0) for k in katilimlar if k.sube_id == sid)
        ort_net = round(ort_net / k_sayi, 2) if k_sayi else 0
        ort_puan = sum((k.toplam_puan or 0) for k in katilimlar if k.sube_id == sid)
        ort_puan = round(ort_puan / k_sayi, 2) if k_sayi else 0
        sube_ozetleri.append({
            'sube': sube,
            'katilimci': k_sayi,
            'ortalama_net': ort_net,
            'ortalama_puan': ort_puan,
        })
    sube_ozetleri.sort(key=lambda x: -x['ortalama_puan'])

    return render_template('deneme_sinavi/rapor.html',
                           sinav=sinav,
                           dersler=dersler,
                           katilimlar=katilimlar,
                           ders_ortalamalari=ders_ortalamalari,
                           sube_ozetleri=sube_ozetleri)
