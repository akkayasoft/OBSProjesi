"""Multi-tenant destek paketi.

Ana fikir:
- Master DB (obs_master): tenant listesi
- Her tenant icin ayri Postgres DB (obs_<slug>)
- Istegi host'tan cozumleyip SQLAlchemy session'ini tenant engine'ine bagla

Kullanim:
    # app/__init__.py icinde
    from app.tenancy import init_tenancy
    init_tenancy(app)
"""
from flask import Flask

from .master import init_master
from .middleware import init_tenant_middleware
from .cli import register_cli


def init_tenancy(app: Flask) -> None:
    """App factory'den cagrilir. Flag aciksa middleware da devreye girer."""
    init_master(app)            # master DB engine hazir (URL varsa)
    register_cli(app)           # `flask tenant ...` komutlari
    init_tenant_middleware(app)  # before_request (flag aciksa)
