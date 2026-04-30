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

    # App startup'inda Tenant tablosuna sonradan eklenen kolonlari
    # idempotent olarak backfill et (plan, ogrenci_limiti, vs.)
    try:
        _backfill_yeni_kolonlar()
    except Exception:
        pass

    # Yeni eklenen master tablolarini otomatik olustur (idempotent —
    # CREATE TABLE IF NOT EXISTS gibi davranir, mevcut tablolari etkilemez).
    # Boylece ImpersonationToken gibi yeni tablolar deploy sirasinda otomatik
    # olusur, ekstra adim gerekmez.
    try:
        MasterBase.metadata.create_all(bind=_master_engine)
    except Exception as e:
        import sys
        print(f'[tenancy] master create_all uyarisi: {e}', file=sys.stderr)


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
    """Master DB semasi: tenants tablosunu olustur + sonradan eklenen
    kolonlari backfill et (idempotent)."""
    MasterBase.metadata.create_all(bind=get_master_engine())
    _backfill_yeni_kolonlar()


def _backfill_yeni_kolonlar():
    """Tenant tablosuna sonradan eklenen kolonlari (plan, limitler)
    ALTER TABLE ile ekler. create_all() mevcut tabloya yeni kolon
    eklemez; bu fonksiyon idempotent — kolon varsa atlar."""
    from sqlalchemy import text

    eklenecek = [
        ("plan", "VARCHAR(20) NOT NULL DEFAULT 'standart'"),
        ("ogrenci_limiti", "INTEGER"),
        ("kullanici_limiti", "INTEGER"),
        ("ogretmen_limiti", "INTEGER"),
    ]

    try:
        engine = get_master_engine()
    except RuntimeError:
        return

    try:
        with engine.begin() as conn:
            for kolon, sql_tipi in eklenecek:
                # IF NOT EXISTS ile multiple gunicorn worker'in race condition
                # olusturmasini engelle (Postgres 9.6+).
                conn.execute(text(
                    f"ALTER TABLE tenants ADD COLUMN IF NOT EXISTS {kolon} {sql_tipi}"
                ))
    except Exception as e:
        # Master DB hata verirse uygulamayi durdurma — log basit print yeterli
        import sys
        print(f'[tenancy] _backfill_yeni_kolonlar uyarisi: {e}', file=sys.stderr)
