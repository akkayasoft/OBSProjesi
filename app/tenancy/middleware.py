"""Request-level tenant cozumleme.

`before_request` hook'u:
  1. Host header'indan subdomain cikar
  2. Master DB'den tenant kaydini bul
  3. Tenant aktifse g.tenant ve g.tenant_engine set et
  4. Pasif/yok ise 404 veya bakim sayfasi

`teardown_request`:
  - db.session.remove() zaten Flask-SQLAlchemy tarafindan yapilir; ekstra
    isleme gerek yok.
"""
from typing import Optional

from flask import Flask, abort, current_app, g, render_template, request
from sqlalchemy import select

from .models import Tenant
from .master import master_session
from .engines import get_tenant_engine


# Subdomain'den istisnalar (tenant cozumlemesi atlanacak):
# - 'admin' — master yonetim panelinin kendisi
# - 'www' / '' — ana domaine yonlendirme (opsiyonel)
RESERVED_SUBDOMAINS = {'admin', 'www'}


def _extract_subdomain(host: str, root_domain: str) -> Optional[str]:
    """host='x.obs.akkayasoft.com', root='obs.akkayasoft.com' -> 'x'.

    host root_domain'e esitse veya onunla bitmiyor ise None.
    """
    host = (host or '').split(':', 1)[0].lower().strip()
    root_domain = (root_domain or '').lower().strip()
    if not host or not root_domain:
        return None
    if host == root_domain:
        return None
    if not host.endswith('.' + root_domain):
        return None
    sub = host[:-len(root_domain) - 1]  # sondaki '.root' atilir
    # Coklu subdomain destegi istenirse buraya mantik eklenebilir;
    # simdilik yalnizca tek seviyeli kabul edilir.
    if '.' in sub:
        return None
    return sub


def _resolve_tenant_from_request(app: Flask) -> Optional[Tenant]:
    root = app.config.get('TENANT_ROOT_DOMAIN')
    if not root:
        return None
    # Dev kolayligi: TENANT_DEFAULT_SLUG ayarli ise root domain'de
    # (veya localhost'ta) otomatik bu slug kullanilir.
    sub = _extract_subdomain(request.host, root)
    if sub is None:
        # Root veya farkli domain; default tenant varsa onu kullan
        sub = app.config.get('TENANT_DEFAULT_SLUG')
        if not sub:
            return None
    if sub in RESERVED_SUBDOMAINS:
        return None

    with master_session() as s:
        tenant = s.execute(
            select(Tenant).where(Tenant.slug == sub)
        ).scalar_one_or_none()
        if tenant is None:
            return None
        if not tenant.aktif_mi:
            # Aktif degilse detayli yanit icin expunge edip don
            s.expunge(tenant)
            return tenant
        s.expunge(tenant)
        return tenant


def init_tenant_middleware(app: Flask) -> None:
    """Multi-tenant flag'i aciksa before_request hook'unu kaydet."""
    if not app.config.get('MULTITENANT_ENABLED'):
        return

    @app.before_request
    def _tenant_resolver():
        # Statik, health ve yasal (tenant'tan bagimsiz) path'leri atla
        p = request.path
        if (p.startswith('/static/') or p.startswith('/_health')
                or p.startswith('/gizlilik')):
            return

        tenant = _resolve_tenant_from_request(app)
        if tenant is None:
            # Tenant bulunamadi -> 404
            return render_template('tenancy/tenant_bulunamadi.html'), 404
        if not tenant.aktif_mi:
            return render_template(
                'tenancy/tenant_pasif.html', tenant=tenant
            ), 503

        g.tenant = tenant
        g.tenant_engine = get_tenant_engine(tenant.db_name)
