import os
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


class Config:
    TIMEZONE = KST
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily"
    )
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL",
        "mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test",
    )
    REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/1")


class ProductionConfig(Config):
    pass


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
