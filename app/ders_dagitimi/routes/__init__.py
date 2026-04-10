def register_routes(bp):
    from app.ders_dagitimi.routes import dashboard  # noqa: F401
    from app.ders_dagitimi.routes import ders  # noqa: F401
    from app.ders_dagitimi.routes import program  # noqa: F401
    from app.ders_dagitimi.routes import atama  # noqa: F401

    bp.register_blueprint(dashboard.bp)
    bp.register_blueprint(ders.bp, url_prefix='/ders')
    bp.register_blueprint(program.bp, url_prefix='/program')
    bp.register_blueprint(atama.bp, url_prefix='/atama')
