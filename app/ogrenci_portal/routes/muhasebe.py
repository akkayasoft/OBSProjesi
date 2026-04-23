"""Veli / ogrenci icin odeme durumu goruntuleme (salt okunur).

Veli veya ogrenci buradan oz plan bilgilerini, taksitlerini, kalan
borcunu gorur. Butonlar ve islem actionlari yok — tahsilat ve planlama
muhasebe roluyle kurum icinde yapilir.
"""
from flask import Blueprint, render_template
from flask_login import login_required
from app.utils import role_required
from app.models.muhasebe import OdemePlani, Taksit
from app.ogrenci_portal.helpers import get_current_ogrenci, get_current_veli

bp = Blueprint('muhasebe_portal', __name__, url_prefix='/muhasebe')


@bp.route('/')
@login_required
@role_required('ogrenci', 'veli', 'admin')
def index():
    ogrenci = get_current_ogrenci()
    veli = get_current_veli()

    planlar = []
    toplam_borc = 0.0
    toplam_odenen = 0.0
    geciken_sayisi = 0

    if ogrenci:
        planlar = (OdemePlani.query
                   .filter_by(ogrenci_id=ogrenci.id)
                   .order_by(OdemePlani.olusturma_tarihi.desc())
                   .all())

        for plan in planlar:
            # Taksitleri listeye al ve vade tarihine gore sirala
            plan._taksit_listesi = sorted(
                plan.taksitler.all(),
                key=lambda t: (t.taksit_no, t.vade_tarihi)
            )
            for t in plan._taksit_listesi:
                kalan = float(t.tutar) - float(t.odenen_tutar or 0)
                toplam_odenen += float(t.odenen_tutar or 0)
                if plan.durum == 'aktif' and t.durum not in ('odendi', 'iptal'):
                    toplam_borc += max(kalan, 0)
                    if t.gecikti_mi and kalan > 0:
                        geciken_sayisi += 1

    return render_template(
        'ogrenci_portal/muhasebe.html',
        ogrenci=ogrenci,
        veli=veli,
        planlar=planlar,
        toplam_borc=toplam_borc,
        toplam_odenen=toplam_odenen,
        geciken_sayisi=geciken_sayisi,
    )
