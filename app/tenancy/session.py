"""Tenant-aware Session sinifi.

Flask-SQLAlchemy'nin `db.session`'u bir scoped_session — onun altinda donen
Session nesnelerinin `get_bind()` metodunu override ederek, istek
baglamindayken `g.tenant_engine`'i kullaniriz. Baglam yoksa veya tenant
cozulmemisse Flask-SQLAlchemy'nin default engine'ine duseriz.

Bu yaklasimla var olan `db.session.query(...)` kullanimi DEGISMEDEN calisir;
sadece arka planda dogru DB'ye baglanir.
"""
from flask import g, has_request_context
from flask_sqlalchemy.session import Session as FlaskSQLAlchemySession


class TenantAwareSession(FlaskSQLAlchemySession):
    """Session.get_bind() override — tenant engine'i varsa onu donerir."""

    def get_bind(self, mapper=None, clause=None, bind=None, **kwargs):
        if bind is not None:
            return bind
        if has_request_context():
            engine = getattr(g, 'tenant_engine', None)
            if engine is not None:
                return engine
        return super().get_bind(mapper=mapper, clause=clause, bind=bind,
                                **kwargs)
