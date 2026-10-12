def register_blueprints(app):
    from app.api.guests import bp as guests_bp
    from app.api.health import bp as health_bp
    from app.api.me import bp as me_bp
    from app.api.oauth import bp as oauth_bp
    from app.api.puzzles import bp as puzzles_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(guests_bp, url_prefix="/api/v1")
    app.register_blueprint(puzzles_bp, url_prefix="/api/v1")
    app.register_blueprint(me_bp, url_prefix="/api/v1")
    app.register_blueprint(oauth_bp, url_prefix="/api/v1")
