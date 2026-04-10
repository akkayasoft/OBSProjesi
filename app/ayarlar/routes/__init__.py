def register_routes(bp):
    from app.ayarlar.routes import dashboard  # noqa: F401
    from app.ayarlar.routes import genel  # noqa: F401
    from app.ayarlar.routes import akademik  # noqa: F401
    from app.ayarlar.routes import muhasebe_ayar  # noqa: F401
    from app.ayarlar.routes import iletisim_ayar  # noqa: F401
    from app.ayarlar.routes import guvenlik  # noqa: F401
    from app.ayarlar.routes import yedekleme  # noqa: F401
    from app.ayarlar.routes import yetkilendirme  # noqa: F401

    bp.register_blueprint(dashboard.bp)
    bp.register_blueprint(genel.bp)
    bp.register_blueprint(akademik.bp)
    bp.register_blueprint(muhasebe_ayar.bp)
    bp.register_blueprint(iletisim_ayar.bp)
    bp.register_blueprint(guvenlik.bp)
    bp.register_blueprint(yedekleme.bp)
    bp.register_blueprint(yetkilendirme.bp)
