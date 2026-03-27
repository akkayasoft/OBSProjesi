def register_routes(bp):
    from app.devamsizlik.routes import yoklama  # noqa: F401
    from app.devamsizlik.routes import rapor  # noqa: F401

    bp.register_blueprint(yoklama.bp, url_prefix='/yoklama')
    bp.register_blueprint(rapor.bp, url_prefix='/rapor')
