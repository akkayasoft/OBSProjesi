def register_routes(bp):
    from app.kulupler.routes import dashboard  # noqa: F401
    from app.kulupler.routes import kulup  # noqa: F401
    from app.kulupler.routes import uyelik  # noqa: F401
    from app.kulupler.routes import etkinlik  # noqa: F401

    bp.register_blueprint(dashboard.bp)
    bp.register_blueprint(kulup.bp, url_prefix='/kulup')
    bp.register_blueprint(uyelik.bp)
    bp.register_blueprint(etkinlik.bp, url_prefix='/etkinlik')
