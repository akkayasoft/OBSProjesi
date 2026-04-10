def register_routes(bp):
    from app.karne.routes import karne  # noqa: F401
    from app.karne.routes import transkript  # noqa: F401

    bp.register_blueprint(karne.bp)
    bp.register_blueprint(transkript.bp, url_prefix='/transkript')
