def register_routes(bp):
    from app.yurt.routes import oda, kayit, yoklama

    bp.register_blueprint(oda.bp, url_prefix='/oda')
    bp.register_blueprint(kayit.bp, url_prefix='/kayit')
    bp.register_blueprint(yoklama.bp, url_prefix='/yoklama')
