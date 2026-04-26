def register_routes(bp):
    from app.kayit.routes import ogrenci  # noqa: F401
    from app.kayit.routes import sinif  # noqa: F401
    from app.kayit.routes import donem  # noqa: F401
    from app.kayit.routes import belge  # noqa: F401
    from app.kayit.routes import veli  # noqa: F401

    bp.register_blueprint(ogrenci.bp, url_prefix='/ogrenci')
    bp.register_blueprint(sinif.bp, url_prefix='/sinif')
    bp.register_blueprint(donem.bp, url_prefix='/donem')
    bp.register_blueprint(belge.bp, url_prefix='/belge')
    bp.register_blueprint(veli.bp, url_prefix='/veli')
