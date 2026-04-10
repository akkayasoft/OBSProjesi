def register_routes(bp):
    from app.denetim.routes import log
    bp.register_blueprint(log.bp)
