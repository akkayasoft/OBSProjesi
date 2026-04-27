"""Platform admin (sistem) UI route'lari — /sistem/ prefix'inde.

Tenant'lardan tamamen bagimsiz; master DB'de yasayan PlatformAdmin
hesaplariyla giris yapilir. Tum tenant'lari toplu yonetmek, yeni
dershane eklemek, plan/limit duzenlemek, askiya almak icin.
"""
from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

from flask import (Blueprint, render_template, redirect, url_for, flash,
                    request, abort)
from sqlalchemy import or_, func

from app.tenancy.master import master_session
from app.tenancy.models import Tenant, PlatformAdmin, PlatformAuditLog
from app.tenancy.limitler import PLAN_LIMITLERI
from app.tenancy.sistem_auth import (
    aktif_platform_admin, platform_admin_login, platform_admin_logout,
    platform_admin_required, audit_kaydet,
)


bp = Blueprint('sistem', __name__, url_prefix='/sistem')


def _safe_next(url: str | None) -> str | None:
    """Open-redirect'e karsi: sadece ayni site path'ine izin ver."""
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.netloc:
        return None
    if not parsed.path.startswith('/sistem/'):
        return None
    return url


# === Auth ===

@bp.route('/giris', methods=['GET', 'POST'])
def giris():
    # Zaten giris yapildiysa dashboard'a
    if aktif_platform_admin():
        return redirect(url_for('sistem.dashboard'))

    hata = None
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        sifre = request.form.get('password') or ''

        with master_session() as s:
            admin = s.query(PlatformAdmin).filter(
                func.lower(PlatformAdmin.username) == username.lower(),
                PlatformAdmin.aktif.is_(True),
            ).first()
            if admin and admin.check_password(sifre):
                admin.son_giris = datetime.utcnow()
                audit_kaydet(s, admin, 'login')
                s.commit()
                platform_admin_login(admin)
                hedef = _safe_next(request.args.get('next')) or url_for('sistem.dashboard')
                return redirect(hedef)
            hata = 'Kullanici adi veya sifre hatali.'

    return render_template('sistem/giris.html', hata=hata)


@bp.route('/cikis', methods=['POST'])
def cikis():
    admin = aktif_platform_admin()
    if admin:
        with master_session() as s:
            audit_kaydet(s, admin, 'logout')
            s.commit()
    platform_admin_logout()
    return redirect(url_for('sistem.giris'))


# === Dashboard ===

@bp.route('/')
@platform_admin_required
def dashboard():
    arama = (request.args.get('arama') or '').strip()
    durum = (request.args.get('durum') or '').strip()

    with master_session() as s:
        q = s.query(Tenant)
        if durum:
            q = q.filter(Tenant.durum == durum)
        if arama:
            like = f'%{arama}%'
            q = q.filter(or_(
                Tenant.slug.ilike(like),
                Tenant.ad.ilike(like),
                Tenant.iletisim_email.ilike(like),
            ))
        tenants = q.order_by(Tenant.created_at.desc()).all()
        for t in tenants:
            s.expunge(t)

        # Ozet sayilari
        toplam = s.query(func.count(Tenant.id)).scalar() or 0
        aktif = s.query(func.count(Tenant.id)).filter(Tenant.durum == 'aktif').scalar() or 0
        askida = s.query(func.count(Tenant.id)).filter(Tenant.durum == 'askida').scalar() or 0

    return render_template(
        'sistem/dashboard.html',
        tenants=tenants,
        toplam=toplam,
        aktif=aktif,
        askida=askida,
        arama=arama,
        durum=durum,
        planlar=PLAN_LIMITLERI,
    )


# === Tenant detay & duzenleme ===

@bp.route('/tenant/<int:tenant_id>')
@platform_admin_required
def tenant_detay(tenant_id):
    with master_session() as s:
        tenant = s.query(Tenant).filter_by(id=tenant_id).first_or_404()
        s.expunge(tenant)

        # Audit log son 20 kayit
        loglar = (s.query(PlatformAuditLog)
                  .filter(PlatformAuditLog.tenant_id == tenant_id)
                  .order_by(PlatformAuditLog.created_at.desc())
                  .limit(20).all())
        for l in loglar:
            s.expunge(l)

    # Tenant'in DB'sinden istatistik (best-effort)
    istatistik = _tenant_istatistik(tenant.db_name)

    return render_template(
        'sistem/tenant_detay.html',
        tenant=tenant,
        loglar=loglar,
        istatistik=istatistik,
        planlar=PLAN_LIMITLERI,
    )


def _tenant_istatistik(db_name: str) -> dict:
    """Tenant'in kendi DB'sinden ogrenci/ogretmen/kullanici sayisini cek.

    Hata olursa boş dict dondur — sayfa render olmaya devam etsin.
    """
    try:
        from app.tenancy.engines import get_tenant_engine
        from sqlalchemy.orm import Session as SAQSession
        from app.models.user import User
        from app.models.muhasebe import Ogrenci

        engine = get_tenant_engine(db_name)
        with SAQSession(engine) as ss:
            ogrenci = ss.query(func.count(Ogrenci.id)).filter(Ogrenci.aktif.is_(True)).scalar() or 0
            ogretmen = ss.query(func.count(User.id)).filter(
                User.rol == 'ogretmen', User.aktif.is_(True)
            ).scalar() or 0
            kullanici = ss.query(func.count(User.id)).filter(User.aktif.is_(True)).scalar() or 0
        return {'ogrenci': ogrenci, 'ogretmen': ogretmen, 'kullanici': kullanici}
    except Exception:
        return {}


@bp.route('/tenant/<int:tenant_id>/duzenle', methods=['POST'])
@platform_admin_required
def tenant_duzenle(tenant_id):
    yeni_plan = (request.form.get('plan') or '').strip()
    if yeni_plan not in PLAN_LIMITLERI:
        flash('Geçersiz plan.', 'danger')
        return redirect(url_for('sistem.tenant_detay', tenant_id=tenant_id))

    def _int_or_none(key):
        v = (request.form.get(key) or '').strip()
        if v == '':
            return None
        try:
            return max(0, int(v))
        except ValueError:
            return None

    yeni_ogrenci = _int_or_none('ogrenci_limiti')
    yeni_ogretmen = _int_or_none('ogretmen_limiti')
    yeni_kullanici = _int_or_none('kullanici_limiti')
    iletisim_email = (request.form.get('iletisim_email') or '').strip() or None
    iletisim_telefon = (request.form.get('iletisim_telefon') or '').strip() or None
    abonelik_bitis_str = (request.form.get('abonelik_bitis') or '').strip()
    abonelik_bitis = None
    if abonelik_bitis_str:
        try:
            from datetime import date
            abonelik_bitis = date.fromisoformat(abonelik_bitis_str)
        except ValueError:
            pass

    admin = aktif_platform_admin()
    with master_session() as s:
        tenant = s.query(Tenant).filter_by(id=tenant_id).first_or_404()
        eski_plan = tenant.plan
        tenant.plan = yeni_plan
        tenant.ogrenci_limiti = yeni_ogrenci
        tenant.ogretmen_limiti = yeni_ogretmen
        tenant.kullanici_limiti = yeni_kullanici
        tenant.iletisim_email = iletisim_email
        tenant.iletisim_telefon = iletisim_telefon
        tenant.abonelik_bitis = abonelik_bitis
        audit_kaydet(s, admin, 'tenant_update', tenant=tenant,
                      detay=f'plan: {eski_plan} -> {yeni_plan}, '
                            f'ogrenci_limit={yeni_ogrenci}, '
                            f'ogretmen_limit={yeni_ogretmen}, '
                            f'kullanici_limit={yeni_kullanici}')
        s.commit()
    flash('Tenant bilgileri güncellendi.', 'success')
    return redirect(url_for('sistem.tenant_detay', tenant_id=tenant_id))


@bp.route('/tenant/<int:tenant_id>/durum', methods=['POST'])
@platform_admin_required
def tenant_durum(tenant_id):
    yeni_durum = (request.form.get('durum') or '').strip()
    if yeni_durum not in ('aktif', 'askida'):
        abort(400)
    admin = aktif_platform_admin()
    with master_session() as s:
        tenant = s.query(Tenant).filter_by(id=tenant_id).first_or_404()
        eski = tenant.durum
        tenant.durum = yeni_durum
        audit_kaydet(s, admin,
                     'tenant_suspend' if yeni_durum == 'askida' else 'tenant_activate',
                     tenant=tenant,
                     detay=f'{eski} -> {yeni_durum}')
        s.commit()
        slug = tenant.slug
        ad = tenant.ad
    flash(f'"{ad}" durumu "{yeni_durum}" olarak güncellendi.', 'success')
    return redirect(url_for('sistem.tenant_detay', tenant_id=tenant_id))


# === Audit log ===

@bp.route('/audit')
@platform_admin_required
def audit():
    sayfa = request.args.get('sayfa', 1, type=int)
    LIMIT = 50
    with master_session() as s:
        q = (s.query(PlatformAuditLog)
             .order_by(PlatformAuditLog.created_at.desc()))
        toplam = q.count()
        loglar = q.offset((sayfa - 1) * LIMIT).limit(LIMIT).all()
        for l in loglar:
            s.expunge(l)
    son_sayfa = max(1, (toplam + LIMIT - 1) // LIMIT)
    return render_template('sistem/audit.html',
                           loglar=loglar,
                           sayfa=sayfa,
                           son_sayfa=son_sayfa,
                           toplam=toplam)
