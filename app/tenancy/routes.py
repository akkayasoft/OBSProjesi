"""Tenant abonelik yonetimi UI (sistem admin / dershane admin).

- /abonelik/             — kendi tenant'imizin plan + limit ozeti + degistir formu
- /abonelik/duzenle      — POST: plan ve override limit'leri guncelle

Yetki: sadece 'admin' rolu (her tenant'in admin kullanicisi). Yonetici plan
degistiremesin (kendi indirimini yapma engellensin); admin yapar.

Kendi tenant'imizdan baska tenant'a dokunulmaz — master DB'de g.tenant.id
filtresi kullanilir.
"""
from __future__ import annotations

from flask import Blueprint, render_template, redirect, url_for, flash, request, g, abort
from flask_login import login_required

from app.utils import role_required
from app.tenancy.master import master_session
from app.tenancy.models import Tenant
from app.tenancy.limitler import PLAN_LIMITLERI, kullanim_durumu


bp = Blueprint('abonelik', __name__, url_prefix='/abonelik')


def _aktif_tenant():
    """Mevcut request'in tenant'i (master DB'de tracked olan kayit)."""
    return getattr(g, 'tenant', None)


@bp.route('/')
@login_required
@role_required('admin')
def index():
    tenant = _aktif_tenant()
    if not tenant:
        flash('Aktif tenant tespit edilemedi.', 'danger')
        return redirect(url_for('main.dashboard'))

    kullanim = kullanim_durumu()

    return render_template(
        'tenancy/abonelik_detay.html',
        tenant=tenant,
        kullanim=kullanim,
        planlar=PLAN_LIMITLERI,
    )


@bp.route('/duzenle', methods=['POST'])
@login_required
@role_required('admin')
def duzenle():
    tenant = _aktif_tenant()
    if not tenant:
        abort(404)

    yeni_plan = (request.form.get('plan') or '').strip()
    if yeni_plan not in PLAN_LIMITLERI:
        flash('Geçersiz plan kodu.', 'danger')
        return redirect(url_for('abonelik.index'))

    # Override limitleri (bos = preset kullan)
    def _int_or_none(key):
        val = (request.form.get(key) or '').strip()
        if val == '':
            return None
        try:
            n = int(val)
            return max(0, n)  # negatif girilmesin
        except ValueError:
            return None

    yeni_ogrenci = _int_or_none('ogrenci_limiti')
    yeni_ogretmen = _int_or_none('ogretmen_limiti')
    yeni_kullanici = _int_or_none('kullanici_limiti')

    # Master DB'de guncelle
    with master_session() as s:
        master_tenant = s.query(Tenant).filter_by(id=tenant.id).first()
        if not master_tenant:
            abort(404)
        master_tenant.plan = yeni_plan
        master_tenant.ogrenci_limiti = yeni_ogrenci
        master_tenant.ogretmen_limiti = yeni_ogretmen
        master_tenant.kullanici_limiti = yeni_kullanici
        s.commit()

    # g.tenant'i de tazele (sonraki request'lerde middleware tekrar okur)
    tenant.plan = yeni_plan
    tenant.ogrenci_limiti = yeni_ogrenci
    tenant.ogretmen_limiti = yeni_ogretmen
    tenant.kullanici_limiti = yeni_kullanici

    flash(f'Abonelik planı "{PLAN_LIMITLERI[yeni_plan]["ad"]}" olarak güncellendi.',
          'success')
    return redirect(url_for('abonelik.index'))
