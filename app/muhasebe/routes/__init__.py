def register_routes(bp):
    from app.muhasebe.routes import gelir_gider  # noqa: F401
    from app.muhasebe.routes import ogrenci_odeme  # noqa: F401
    from app.muhasebe.routes import personel_odeme  # noqa: F401
    from app.muhasebe.routes import banka  # noqa: F401
    from app.muhasebe.routes import raporlar  # noqa: F401

    bp.register_blueprint(gelir_gider.bp, url_prefix='/gelir-gider')
    bp.register_blueprint(ogrenci_odeme.bp, url_prefix='/ogrenci-odeme')
    bp.register_blueprint(personel_odeme.bp, url_prefix='/personel-odeme')
    bp.register_blueprint(banka.bp, url_prefix='/banka')
    bp.register_blueprint(raporlar.bp, url_prefix='/raporlar')
