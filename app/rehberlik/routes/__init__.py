def register_routes(bp):
    from app.rehberlik.routes import dashboard  # noqa: F401
    from app.rehberlik.routes import gorusme  # noqa: F401
    from app.rehberlik.routes import profil  # noqa: F401
    from app.rehberlik.routes import veli  # noqa: F401
    from app.rehberlik.routes import plan  # noqa: F401

    bp.register_blueprint(dashboard.bp)
    bp.register_blueprint(gorusme.bp, url_prefix='/gorusme')
    bp.register_blueprint(profil.bp, url_prefix='/profil')
    bp.register_blueprint(veli.bp, url_prefix='/veli')
    bp.register_blueprint(plan.bp, url_prefix='/plan')
