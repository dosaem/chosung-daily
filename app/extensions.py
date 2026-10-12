import redis
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
redis_client: redis.Redis | None = None


def init_redis(app):
    global redis_client
    redis_client = redis.from_url(app.config["REDIS_URL"], decode_responses=True)
    return redis_client
