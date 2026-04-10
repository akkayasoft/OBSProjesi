def register_routes(bp):
    from app.raporlama.routes import dashboard, ogrenci, personel, akademik

    bp.register_blueprint(dashboard.bp)
    bp.register_blueprint(ogrenci.bp, url_prefix='/ogrenci')
    bp.register_blueprint(personel.bp, url_prefix='/personel')
    bp.register_blueprint(akademik.bp, url_prefix='/akademik')
