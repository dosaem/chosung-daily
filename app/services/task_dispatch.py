"""요청·서비스 코드에서 Celery 태스크를 큐에 넣는 입구.

`celery_app.py` 를 import 하지 않는다 — 그 모듈은 import 되는 순간 `create_app()` 으로
자기 Flask 앱을 하나 더 만들고(테스트에선 development 설정 앱), app 패키지에서
그걸 끌어오면 순환 import 가 된다. 브로커 주소만 알면 이름으로 보낼 수 있으므로
얇은 클라이언트를 따로 만든다. 테스트는 이 함수를 monkeypatch 한다.
"""

from celery import Celery
from flask import current_app


def enqueue_task(name: str, *args) -> None:
    Celery(broker=current_app.config["REDIS_URL"]).send_task(name, args=list(args))
