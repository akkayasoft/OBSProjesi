def register_routes(bp):
    from app.servis.routes import dashboard  # noqa: F401
    from app.servis.routes import guzergah  # noqa: F401
    from app.servis.routes import durak  # noqa: F401
    from app.servis.routes import arac  # noqa: F401
    from app.servis.routes import kayit  # noqa: F401

    bp.register_blueprint(dashboard.bp)
    bp.register_blueprint(guzergah.bp, url_prefix='/guzergah')
    bp.register_blueprint(durak.bp)
    bp.register_blueprint(arac.bp, url_prefix='/arac')
    bp.register_blueprint(kayit.bp, url_prefix='/kayit')
