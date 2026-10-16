import os
import time

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from app.access_log import register_access_log
from app.admin import register_admin
from app.api import register_blueprints
from app.cli import register_commands
from app.config import CONFIG_BY_NAME
from app.errors import register_error_handlers
from app.extensions import db, init_oauth, init_redis, migrate
from app.observability import init_sentry
from app.web import register_web


def create_app(config_name: str | None = None) -> Flask:
    config_name = config_name or os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__, template_folder="../web/templates", static_folder="../web/static")
    app.config.from_object(CONFIG_BY_NAME[config_name])
    # Sentry 의 environment 태그와 운영 중 설정 확인용. 설정 클래스마다
    # 같은 문자열을 또 적지 않으려고 고른 이름을 그대로 넣는다.
    app.config["ENV_NAME"] = config_name

    init_sentry(app)

    # 정적 파일이 브라우저에 몇 시간씩 캐싱돼서, 배포해도 유저가 새 app.js/style.css를
    # 못 받는 문제(실제로 겪음 — 캐시 안 지우면 코드가 바뀐 뒤에도 옛 JS가 계속 돔)를
    # 막으려고, 템플릿에서 정적 파일 URL 뒤에 붙일 버전 값을 프로세스 시작 시각으로 둔다.
    # 배포(=재시작)마다 바뀌니 그때마다 캐시가 새로 받아진다.
    app.jinja_env.globals["asset_version"] = int(time.time())

    if app.config["TRUST_PROXY"]:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=app.config["PROXY_FIX_X_FOR"], x_proto=1)

    db.init_app(app)
    migrate.init_app(app, db)
    init_redis(app)
    init_oauth(app)

    from app import models  # noqa: F401  (db.metadata에 테이블 등록)

    register_blueprints(app)
    register_web(app)
    register_admin(app)
    register_error_handlers(app)
    # 접속기록은 라우트가 아니라 응답 훅이다 — 블루프린트가 다 붙은 뒤에 건다.
    register_access_log(app)
    register_commands(app)

    return app
