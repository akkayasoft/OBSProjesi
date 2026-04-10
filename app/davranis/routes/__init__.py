def register_routes(bp):
    from app.davranis.routes import kayit  # noqa: F401
    from app.davranis.routes import kural  # noqa: F401
    from app.davranis.routes import rapor  # noqa: F401

    bp.register_blueprint(kayit.bp, url_prefix='/kayit')
    bp.register_blueprint(kural.bp, url_prefix='/kural')
    bp.register_blueprint(rapor.bp, url_prefix='/rapor')
