def register_routes(bp):
    from app.saglik.routes import dashboard  # noqa: F401
    from app.saglik.routes import kayit  # noqa: F401
    from app.saglik.routes import revir  # noqa: F401
    from app.saglik.routes import asi  # noqa: F401
    from app.saglik.routes import tarama  # noqa: F401

    bp.register_blueprint(dashboard.bp)
    bp.register_blueprint(kayit.bp, url_prefix='/kayit')
    bp.register_blueprint(revir.bp, url_prefix='/revir')
    bp.register_blueprint(asi.bp, url_prefix='/asi')
    bp.register_blueprint(tarama.bp, url_prefix='/tarama')
