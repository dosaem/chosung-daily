import os
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


class Config:
    TIMEZONE = KST
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily?charset=utf8mb4",
    )
    # MySQL 기본 격리수준(REPEATABLE READ)에서는 트랜잭션 안의 일반 SELECT가
    # 트랜잭션 시작 시점 스냅샷을 계속 본다 — SELECT ... FOR UPDATE로 잠금을
    # 걸고 기다려서 받아도, 그 뒤의 일반 SELECT는 잠금을 건 시점이 아니라
    # "이 트랜잭션이 맨 처음 뭔가를 읽은 시점"의 스냅샷을 쓴다. FOR UPDATE 기반
    # 동시성 제어(app/services/guess_service.py)가 막 커밋된 데이터를 보려면
    # READ COMMITTED가 필요하다 (MySQL 공식 문서가 이 조합을 권장).
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "isolation_level": "READ COMMITTED"}
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL",
        "mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test?charset=utf8mb4",
    )
    REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/1")


class ProductionConfig(Config):
    pass


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
