"""Platform admin (sistem) authentication ve yetki helper'lari.

Flask-Login'den BAGIMSIZ. session['platform_admin_id'] uzerinden takip
ediyoruz, Flask-Login'in user_id'sine karistirmiyoruz — bir kullanici
hem tenant admini hem platform admini olabilir, ikisi ayri oturum.
"""
from __future__ import annotations

from functools import wraps
from typing import Optional

from flask import session, redirect, url_for, request, g, abort
from sqlalchemy.orm import Session

from app.tenancy.master import master_session
from app.tenancy.models import PlatformAdmin, PlatformAuditLog


SESSION_KEY = 'platform_admin_id'


def aktif_platform_admin() -> Optional[PlatformAdmin]:
    """Mevcut request'in platform admini (varsa). g cache'ler."""
    cached = getattr(g, '_platform_admin', 'unset')
    if cached != 'unset':
        return cached

    admin_id = session.get(SESSION_KEY)
    if not admin_id:
        g._platform_admin = None
        return None

    with master_session() as s:
        admin = s.query(PlatformAdmin).filter_by(id=admin_id, aktif=True).first()
        if admin:
            # Detached object — session kapanmadan once gerekli alanlari yukle
            s.expunge(admin)
        g._platform_admin = admin
        return admin


def platform_admin_login(admin: PlatformAdmin) -> None:
    """Session'a admin_id yaz."""
    session[SESSION_KEY] = admin.id
    session.permanent = True


def platform_admin_logout() -> None:
    session.pop(SESSION_KEY, None)
    if hasattr(g, '_platform_admin'):
        delattr(g, '_platform_admin')


def platform_admin_required(view):
    """Sayfaya/endpoint'e erisim icin platform admin girisi ister."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        admin = aktif_platform_admin()
        if not admin:
            return redirect(url_for('sistem.giris', next=request.path))
        return view(*args, **kwargs)
    return wrapper


def audit_kaydet(s: Session, admin: PlatformAdmin | None,
                  aksiyon: str,
                  tenant=None,
                  detay: str | None = None) -> None:
    """Master session uzerinden audit log kaydi olustur.

    s: cagiranin acmis oldugu master session — commit cagiran sorumludur.
    """
    log = PlatformAuditLog(
        admin_id=admin.id if admin else None,
        admin_username=admin.username if admin else None,
        tenant_id=tenant.id if tenant else None,
        tenant_slug=tenant.slug if tenant else None,
        aksiyon=aksiyon,
        detay=detay,
        ip=request.remote_addr if request else None,
    )
    s.add(log)
