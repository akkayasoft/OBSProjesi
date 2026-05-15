def register_routes(bp):
    from app.api.routes import auth_routes
    from app.api.routes import bildirim_routes
    from app.api.routes import devamsizlik_routes
    auth_routes.register(bp)
    bildirim_routes.register(bp)
    devamsizlik_routes.register(bp)
