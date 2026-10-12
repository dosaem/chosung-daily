"""redis_client, 그다음 OAuth 레지스트리까지 같은 함정(모듈 전역 하나를 여러
Flask 앱 인스턴스가 공유)에 두 번 빠졌었다. 둘 다 app.extensions에 앱별로
저장하는 걸로 고쳤는데, 같은 실수를 또 반복하지 않도록 직접 검증해둔다.
"""

from flask import Flask

from app.extensions import get_oauth, get_redis, init_oauth, init_redis


def test_redis_client_does_not_leak_between_flask_apps():
    app_a = Flask("app_a")
    app_a.config["REDIS_URL"] = "redis://localhost:6379/1"
    init_redis(app_a)

    app_b = Flask("app_b")
    app_b.config["REDIS_URL"] = "redis://localhost:6379/2"
    init_redis(app_b)

    with app_a.app_context():
        db_a = get_redis().connection_pool.connection_kwargs["db"]
    with app_b.app_context():
        db_b = get_redis().connection_pool.connection_kwargs["db"]
    with app_a.app_context():
        db_a_again = get_redis().connection_pool.connection_kwargs["db"]

    assert (db_a, db_b, db_a_again) == (1, 2, 1)


def test_oauth_client_does_not_leak_between_flask_apps():
    apple_off = {
        "APPLE_CLIENT_ID": "",
        "APPLE_TEAM_ID": "",
        "APPLE_KEY_ID": "",
        "APPLE_PRIVATE_KEY": "",
    }

    app_a = Flask("app_a")
    app_a.config.update(
        GOOGLE_CLIENT_ID="app-a-id", GOOGLE_CLIENT_SECRET="app-a-secret", **apple_off
    )
    init_oauth(app_a)

    app_b = Flask("app_b")
    app_b.config.update(
        GOOGLE_CLIENT_ID="app-b-id", GOOGLE_CLIENT_SECRET="app-b-secret", **apple_off
    )
    init_oauth(app_b)

    with app_a.app_context():
        client_id_a = get_oauth().create_client("google").client_id
    with app_b.app_context():
        client_id_b = get_oauth().create_client("google").client_id
    with app_a.app_context():
        client_id_a_again = get_oauth().create_client("google").client_id

    assert (client_id_a, client_id_b, client_id_a_again) == ("app-a-id", "app-b-id", "app-a-id")
