def register_routes(bp):
    from app.ders_programi.routes import program  # noqa: F401
    bp.register_blueprint(program.program_bp)
