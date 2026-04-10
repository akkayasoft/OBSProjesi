def register_routes(bp):
    from app.ogrenci_portal.routes import dashboard  # noqa: F401
    from app.ogrenci_portal.routes import notlar  # noqa: F401
    from app.ogrenci_portal.routes import devamsizlik  # noqa: F401
    from app.ogrenci_portal.routes import program  # noqa: F401
    from app.ogrenci_portal.routes import sinavlar  # noqa: F401
    from app.ogrenci_portal.routes import duyurular  # noqa: F401

    bp.register_blueprint(dashboard.bp)
    bp.register_blueprint(notlar.bp)
    bp.register_blueprint(devamsizlik.bp)
    bp.register_blueprint(program.bp)
    bp.register_blueprint(sinavlar.bp)
    bp.register_blueprint(duyurular.bp)
