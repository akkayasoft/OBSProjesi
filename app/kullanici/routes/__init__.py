def register_routes(bp):
    from app.kullanici.routes import dashboard  # noqa: F401
    from app.kullanici.routes import yonetim  # noqa: F401
    from app.kullanici.routes import profil  # noqa: F401

    bp.register_blueprint(dashboard.bp)
    bp.register_blueprint(yonetim.bp)
    bp.register_blueprint(profil.bp)
