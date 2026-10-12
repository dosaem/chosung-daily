from flask import Flask

from app.api import register_blueprints
from app.config import CONFIG_BY_NAME
from app.errors import register_error_handlers
from app.extensions import db, init_redis, migrate


def create_app(config_name: str | None = None) -> Flask:
    import os

    config_name = config_name or os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(CONFIG_BY_NAME[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    init_redis(app)

    register_blueprints(app)
    register_error_handlers(app)

    return app
