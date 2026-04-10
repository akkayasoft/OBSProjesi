def register_routes(bp):
    from app.not_defteri.routes import dashboard  # noqa: F401
    from app.not_defteri.routes import sinav  # noqa: F401
    from app.not_defteri.routes import rapor  # noqa: F401

    bp.register_blueprint(dashboard.bp)
    bp.register_blueprint(sinav.bp, url_prefix='/sinav')
    bp.register_blueprint(rapor.bp, url_prefix='/rapor')
