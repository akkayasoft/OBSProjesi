def register_routes(bp):
    from app.api.routes import auth_routes
    auth_routes.register(bp)
