def register_routes(bp):
    from app.etut.routes import etut  # noqa: F401
    from app.etut.routes import katilim  # noqa: F401
    from app.etut.routes import rapor  # noqa: F401

    bp.register_blueprint(etut.bp)
    bp.register_blueprint(katilim.bp, url_prefix='/katilim')
    bp.register_blueprint(rapor.bp, url_prefix='/rapor')
