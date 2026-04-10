def register_routes(bp):
    from app.belge.routes import belge
    bp.register_blueprint(belge.bp)
