def register_routes(bp):
    from app.envanter.routes import demirbas, hareket

    bp.register_blueprint(demirbas.bp, url_prefix='/demirbas')
    bp.register_blueprint(hareket.bp, url_prefix='/hareket')
