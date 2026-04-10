def register_routes(bp):
    from app.ortak_sinav.routes import sinav  # noqa: F401
    from app.ortak_sinav.routes import sonuc  # noqa: F401
    from app.ortak_sinav.routes import rapor  # noqa: F401

    bp.register_blueprint(sinav.bp, url_prefix='/sinav')
    bp.register_blueprint(sonuc.bp, url_prefix='/sonuc')
    bp.register_blueprint(rapor.bp, url_prefix='/rapor')
