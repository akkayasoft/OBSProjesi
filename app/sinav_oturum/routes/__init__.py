def register_routes(bp):
    from app.sinav_oturum.routes import oturum  # noqa: F401
    from app.sinav_oturum.routes import gozetmen  # noqa: F401
    from app.sinav_oturum.routes import takvim  # noqa: F401

    bp.register_blueprint(oturum.bp, url_prefix='/oturum')
    bp.register_blueprint(gozetmen.bp, url_prefix='/gozetmen')
    bp.register_blueprint(takvim.bp, url_prefix='/takvim')
