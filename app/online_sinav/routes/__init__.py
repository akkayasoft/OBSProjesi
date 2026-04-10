def register_routes(bp):
    from app.online_sinav.routes import dashboard  # noqa: F401
    from app.online_sinav.routes import sinav  # noqa: F401
    from app.online_sinav.routes import soru  # noqa: F401
    from app.online_sinav.routes import uygula  # noqa: F401
    from app.online_sinav.routes import sonuc  # noqa: F401

    bp.register_blueprint(dashboard.bp)
    bp.register_blueprint(sinav.bp, url_prefix='/sinav')
    bp.register_blueprint(soru.bp)
    bp.register_blueprint(uygula.bp, url_prefix='/uygula')
    bp.register_blueprint(sonuc.bp, url_prefix='/sonuc')
