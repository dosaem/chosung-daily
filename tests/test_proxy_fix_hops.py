"""ProxyFix 가 믿는 홉 수(PROXY_FIX_X_FOR) — Caddy 를 앞에 두면 2 다(티켓 47).

틀리면 모든 요청이 도커 게이트웨이 IP 로 보여 rate limit 하나를 전부가 나눠 쓴다.
"""

import os

from flask import request

from app import create_app
from app.config import TestingConfig


def _remote_addr(monkeypatch, hops):
    """testing 설정은 TRUST_PROXY 가 꺼져 있어 production 처럼 켠 앱으로 본다."""
    # 설정값은 import 시점에 환경변수를 읽어 클래스 속성이 된다 — 속성을 직접 바꾼다.
    monkeypatch.setattr(TestingConfig, "PROXY_FIX_X_FOR", hops)
    monkeypatch.setattr(TestingConfig, "TRUST_PROXY", True)
    app = create_app("testing")

    @app.get("/_who")
    def who():
        return request.remote_addr

    with app.test_client() as client:
        return client.get(
            "/_who",
            headers={"X-Forwarded-For": "203.0.113.9, 172.18.0.1"},
            environ_base={"REMOTE_ADDR": "172.18.0.5"},
        ).get_data(as_text=True)


def test_two_hops_see_the_real_client_behind_caddy_and_cloudflared(monkeypatch):
    assert _remote_addr(monkeypatch, 2) == "203.0.113.9"


def test_one_hop_sees_only_the_nearest_proxy(monkeypatch):
    assert _remote_addr(monkeypatch, 1) == "172.18.0.1"


def test_default_is_one_hop():
    assert "PROXY_FIX_X_FOR" not in os.environ, "기본값 검사는 환경변수가 없을 때만 뜻이 있다"
    assert create_app("testing").config["PROXY_FIX_X_FOR"] == 1
