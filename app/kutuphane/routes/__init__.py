def register_routes(bp):
    from app.kutuphane.routes import kitap, odunc

    bp.register_blueprint(kitap.bp, url_prefix='/kitap')
    bp.register_blueprint(odunc.bp, url_prefix='/odunc')
