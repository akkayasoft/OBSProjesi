def register_routes(bp):
    from app.iletisim.routes import dashboard  # noqa: F401
    from app.iletisim.routes import mesaj  # noqa: F401
    from app.iletisim.routes import toplu  # noqa: F401
    from app.iletisim.routes import sablon  # noqa: F401
    from app.iletisim.routes import rehber  # noqa: F401

    bp.register_blueprint(dashboard.bp)
    bp.register_blueprint(mesaj.bp, url_prefix='/mesaj')
    bp.register_blueprint(toplu.bp, url_prefix='/toplu')
    bp.register_blueprint(sablon.bp, url_prefix='/sablon')
    bp.register_blueprint(rehber.bp, url_prefix='/rehber')
