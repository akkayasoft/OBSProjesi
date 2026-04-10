def register_routes(bp):
    from app.kantin.routes import menu, urun, satis

    bp.register_blueprint(menu.bp, url_prefix='/menu')
    bp.register_blueprint(urun.bp, url_prefix='/urun')
    bp.register_blueprint(satis.bp, url_prefix='/satis')
