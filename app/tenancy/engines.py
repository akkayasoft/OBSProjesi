"""Tenant engine onbellek.

Her tenant icin bir SQLAlchemy Engine'i (connection pool) LRU/dict ile
tutariz. Sabit olarak ilk 50 tenant cache'te kalir, sonra en az kullanilan
atilir. Bir Engine cagrisi baglanti havuzu acar; havuzu her istekte
yaratmak cok pahali — bu yuzden process-level cache sart.

Kullanim:
    engine = get_tenant_engine('obs_dershanex')
"""
from collections import OrderedDict
from typing import Optional
from threading import Lock

from flask import current_app
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


_engines: 'OrderedDict[str, Engine]' = OrderedDict()
_lock = Lock()
_MAX_CACHED = 50


def _build_url(db_name: str) -> str:
    template = current_app.config.get('TENANT_DATABASE_URL_TEMPLATE')
    if not template:
        # Yedek: master URL'den db adini degistir
        master = current_app.config.get('MASTER_DATABASE_URL', '')
        if master and '/' in master:
            base, _ = master.rsplit('/', 1)
            return f'{base}/{db_name}'
        raise RuntimeError(
            'TENANT_DATABASE_URL_TEMPLATE yapilandirmasi yok. '
            'Ornek: postgresql://user:pass@host/{db_name}'
        )
    return template.format(db_name=db_name)


def get_tenant_engine(db_name: str) -> Engine:
    """Tenant DB'si icin engine (varsa cache'ten, yoksa yarat+cache'le)."""
    with _lock:
        engine = _engines.get(db_name)
        if engine is not None:
            # LRU yenileme
            _engines.move_to_end(db_name)
            return engine

        url = _build_url(db_name)
        pool_size = current_app.config.get('TENANT_DB_POOL_SIZE', 5)
        engine = create_engine(
            url,
            pool_size=pool_size,
            pool_recycle=1800,   # 30 dk
            pool_pre_ping=True,
            future=True,
        )
        _engines[db_name] = engine

        # Cache sinirini as
        while len(_engines) > _MAX_CACHED:
            _, evicted = _engines.popitem(last=False)
            try:
                evicted.dispose()
            except Exception:
                pass
        return engine


def dispose_all() -> None:
    """Tum cache'teki engine'leri kapat (test/teardown icin)."""
    with _lock:
        for e in _engines.values():
            try:
                e.dispose()
            except Exception:
                pass
        _engines.clear()
