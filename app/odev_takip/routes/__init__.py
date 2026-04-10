def register_routes(bp):
    from app.odev_takip.routes import dashboard  # noqa: F401
    from app.odev_takip.routes import odev  # noqa: F401
    from app.odev_takip.routes import rapor  # noqa: F401

    bp.register_blueprint(dashboard.bp)
    bp.register_blueprint(odev.bp)
    bp.register_blueprint(rapor.bp, url_prefix='/rapor')
