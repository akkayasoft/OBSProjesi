def register_routes(bp):
    from app.kurum.routes import dashboard  # noqa: F401
    from app.kurum.routes import kurum_bilgi  # noqa: F401
    from app.kurum.routes import ogretim_yili  # noqa: F401
    from app.kurum.routes import tatil  # noqa: F401
    from app.kurum.routes import derslik  # noqa: F401

    bp.register_blueprint(dashboard.bp)
    bp.register_blueprint(kurum_bilgi.bp)
    bp.register_blueprint(ogretim_yili.bp)
    bp.register_blueprint(tatil.bp)
    bp.register_blueprint(derslik.bp)
