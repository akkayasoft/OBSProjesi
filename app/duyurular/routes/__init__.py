def register_routes(bp):
    from app.duyurular.routes import dashboard  # noqa: F401
    from app.duyurular.routes import duyuru  # noqa: F401
    from app.duyurular.routes import etkinlik  # noqa: F401
    from app.duyurular.routes import hatirlatma  # noqa: F401

    bp.register_blueprint(dashboard.bp)
    bp.register_blueprint(duyuru.bp, url_prefix='/duyuru')
    bp.register_blueprint(etkinlik.bp, url_prefix='/etkinlik')
    bp.register_blueprint(hatirlatma.bp, url_prefix='/hatirlatma')
