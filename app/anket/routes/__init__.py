def register_routes(bp):
    from app.anket.routes import anket  # noqa: F401
    from app.anket.routes import soru  # noqa: F401
    from app.anket.routes import katilim  # noqa: F401
    from app.anket.routes import sonuc  # noqa: F401

    bp.register_blueprint(anket.bp, url_prefix='/yonetim')
    bp.register_blueprint(soru.bp, url_prefix='/soru')
    bp.register_blueprint(katilim.bp, url_prefix='/katilim')
    bp.register_blueprint(sonuc.bp, url_prefix='/sonuc')
