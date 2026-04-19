"""Master DB engine + session factory.

Kurumsal app'teki `db` (Flask-SQLAlchemy) nesnesinden BAGIMSIZ. Master DB
baska bir Postgres database'inde (ornek: `obs_master`) durur, tenant
listesini tutar.

Kullanim:
    from app.tenancy.master import master_session
    with master_session() as s:
        t = s.query(Tenant).filter_by(slug='x').first()
"""
from contextlib import contextmanager
from typing import Optional

from flask import current_app
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import MasterBase


_master_engine: Optional[Engine] = None
_MasterSession: Optional[sessionmaker] = None


def _build_engine(app) -> Engine:
    url = app.config.get('MASTER_DATABASE_URL')
    if not url:
        raise RuntimeError(
            'MASTER_DATABASE_URL yapilandirmasi bos. Multi-tenant icin '
            'master DB URL\'si zorunlu (ornek: postgresql://u:p@h/obs_master).'
        )
    pool_size = app.config.get('MASTER_DB_POOL_SIZE', 5)
    return create_engine(url, pool_size=pool_size, pool_pre_ping=True,
                         future=True)


def init_master(app) -> None:
    """App baslangicinda master DB engine+session factory'yi hazirla.

    Multi-tenant flag kapaliysa bile tenant CLI komutlarinin calismasi icin
    engine'i hazir etmek mantikli. Ama URL yoksa sessizce skipleriz; o zaman
    yalnizca `flask tenant init-master` bile calismaz ve hata basar.
    """
    global _master_engine, _MasterSession
    if not app.config.get('MASTER_DATABASE_URL'):
        return  # master DB yapilandirilmamis -> single tenant moduna devam
    _master_engine = _build_engine(app)
    _MasterSession = sessionmaker(
        bind=_master_engine, autocommit=False, autoflush=False,
        expire_on_commit=False, future=True,
    )


def get_master_engine() -> Engine:
    if _master_engine is None:
        # Geç baglan (CLI'dan app.config ile cagrilmis olabilir)
        init_master(current_app._get_current_object())
    if _master_engine is None:
        raise RuntimeError('Master DB engine hazirlanmadi.')
    return _master_engine


@contextmanager
def master_session() -> Session:
    """Kisa omurlu master DB oturumu — context manager."""
    if _MasterSession is None:
        init_master(current_app._get_current_object())
    if _MasterSession is None:
        raise RuntimeError('Master DB oturumu hazirlanmadi.')
    s = _MasterSession()
    try:
        yield s
    finally:
        s.close()


def create_master_tables() -> None:
    """Master DB semasi: tenants tablosunu olustur (idempotent)."""
    MasterBase.metadata.create_all(bind=get_master_engine())
