def register_routes(bp):
    from app.ogretmen_portal.routes import dashboard  # noqa: F401
    from app.ogretmen_portal.routes import ders_programi  # noqa: F401
    from app.ogretmen_portal.routes import siniflarim  # noqa: F401
    from app.ogretmen_portal.routes import not_islemleri  # noqa: F401
    from app.ogretmen_portal.routes import yoklama  # noqa: F401
    from app.ogretmen_portal.routes import mesajlar  # noqa: F401
    from app.ogretmen_portal.routes import hakedis  # noqa: F401

    bp.register_blueprint(dashboard.bp)
    bp.register_blueprint(ders_programi.bp)
    bp.register_blueprint(siniflarim.bp)
    bp.register_blueprint(not_islemleri.bp)
    bp.register_blueprint(yoklama.bp)
    bp.register_blueprint(mesajlar.bp)
    bp.register_blueprint(hakedis.bp)
