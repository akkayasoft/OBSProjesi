def register_routes(bp):
    from app.personel.routes import personel  # noqa: F401
    from app.personel.routes import izin  # noqa: F401
    from app.personel.routes import rapor  # noqa: F401

    bp.register_blueprint(personel.bp, url_prefix='/personel')
    bp.register_blueprint(izin.bp, url_prefix='/izin')
    bp.register_blueprint(rapor.bp, url_prefix='/rapor')
