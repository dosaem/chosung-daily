"""개인정보 처리 행위의 **기록 지점** — 어느 요청이 어떤 행위로 접속기록에 남는가.

`app/csrf.py` 와 같은 층이다: 요청 처리에 끼어드는 배선이라 서비스가 아니라
여기에 둔다. 해시 체인·보관 기간·점검은 `app/services/access_log_service.py`.

**왜 `after_request` 한 곳인가.** 라우트마다 데코레이터를 붙이면 (a) 가드가 먼저
403 을 내는 요청은 기록이 안 남고(막힌 접근 시도가 점검에서 가장 보고 싶은 기록이다)
(b) 새 `/admin` 라우트를 추가할 때 붙이는 걸 잊으면 조용히 빠진다. 아래 표를
엔드포인트 이름으로 들고 있으면 라우트가 생길 때 표에 없다는 게 바로 드러난다
(README 설계 판단 "36." 의 표가 이 딕셔너리와 같은지 테스트가 확인한다).

전부 다 남기지는 않는다 — 퍼즐 조회·설정 조회는 개인정보 처리 행위가 아니라서
DB 감사 로그가 아니라 Gunicorn 접근 로그 파일(`gunicorn.conf.py`)에만 남는다.
"""

import logging

from flask import g, request, session

from app.services.access_log_service import record_access

logger = logging.getLogger(__name__)

# 엔드포인트 → 행위 이름. `/admin` 은 조회까지 전부 들어 있다(운영자 화면 열람도
# 개인정보처리시스템 접속이다).
ACTION_BY_ENDPOINT = {
    "admin.words": "admin.word.list",
    "admin.new_word": "admin.word.form",
    "admin.create_word": "admin.word.create",
    "admin.edit_word": "admin.word.form",
    "admin.update_word": "admin.word.update",
    "admin.delete_word": "admin.word.delete",
    "admin.import_form": "admin.csv.form",
    "admin.import_csv": "admin.csv.import",
    "admin.schedule": "admin.schedule.read",
    "admin.replace_form": "admin.schedule.form",
    "admin.replace_word": "admin.schedule.replace",
    "admin.settings_form": "admin.settings.read",
    "admin.save_settings": "admin.settings.save",
    "admin.books": "admin.book.search",
    "admin.add_book_word": "admin.book.create",
    # 플레이어 본인의 개인정보 처리 — 삭제·열람·연결·설정 변경.
    "me.delete_me": "account.delete",
    "web.account_delete_submit": "account.delete",
    "me.my_history": "me.history.read",
    "me.update_me": "me.profile.update",
    "oauth.token_exchange": "account.link",
    "oauth.callback": "account.link",
}

ANONYMOUS_ACTOR = "anonymous"


def mask_email(email: str) -> str:
    """`hsseo@dosaem.com` → `h***@dosaem.com`.

    접속기록은 "누가" 를 가려낼 수 있어야 하지만 로그에 전체 이메일을 남길 이유는
    없다. 운영자는 두 명이라(CONTEXT.md) 첫 글자 + 도메인으로 충분히 구분된다.
    """
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}" if domain else f"{local[:1]}***"


def remember_actor(actor: str) -> None:
    """이 요청의 행위자를 적어 둔다. 인증을 통과시킨 자리에서 부른다.

    응답 시점에 다시 찾지 않는 이유: 계정 삭제는 그 게스트 행을 지우고 세션도
    비우기 때문에, 응답 때는 "누가 지웠는지" 를 알아낼 방법이 없다.
    """
    g.access_log_actor = actor


def _actor() -> str:
    actor = getattr(g, "access_log_actor", None)
    if actor:
        return actor
    guest_id = session.get("current_guest_id")
    return f"guest.{guest_id}" if guest_id else ANONYMOUS_ACTOR


def _target() -> str | None:
    """행위의 대상 식별자 = 라우트 변수의 첫 값(단어 id, 배정 날짜, provider).

    목록·폼처럼 대상이 없는 라우트는 비어 있다.
    """
    return next((str(value) for value in (request.view_args or {}).values()), None)


def register_access_log(app):
    @app.after_request
    def record_personal_data_access(response):
        action = ACTION_BY_ENDPOINT.get(request.endpoint or "")
        if action is None:
            return response
        try:
            record_access(
                action=action,
                actor=_actor(),
                remote_ip=request.remote_addr or "unknown",
                target=_target(),
                status_code=response.status_code,
            )
        except Exception:
            # 기록에 실패했다고 이미 끝난 요청을 500 으로 되돌리지는 않는다 —
            # 계정 삭제는 이미 커밋돼 있어서 "실패" 응답이 더 거짓이다. 대신
            # 스택을 ERROR 로 남겨 Sentry 가 잡게 한다(app/observability.py).
            logger.exception("access_log: failed to record %s", action)
        return response

    return app
