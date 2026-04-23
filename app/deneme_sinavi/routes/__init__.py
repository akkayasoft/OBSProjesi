def register_routes(bp):
    from app.deneme_sinavi.routes import sinav  # noqa: F401
    from app.deneme_sinavi.routes import ders  # noqa: F401
    from app.deneme_sinavi.routes import cevap  # noqa: F401
    from app.deneme_sinavi.routes import rapor  # noqa: F401
    from app.deneme_sinavi.routes import omr  # noqa: F401
    from app.deneme_sinavi.routes import pdf_ithal  # noqa: F401

    bp.register_blueprint(sinav.bp)
    bp.register_blueprint(ders.bp)
    bp.register_blueprint(cevap.bp)
    bp.register_blueprint(rapor.bp)
    bp.register_blueprint(omr.bp)
    bp.register_blueprint(pdf_ithal.bp)
