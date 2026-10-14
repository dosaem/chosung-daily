"""`impeccable detect` 용 스냅샷: 세션이 필요한 `/account/delete` 확인 폼 HTML.

detect 는 URL 로 받은 페이지를 브라우저로 열어 CSS 까지 파싱한다(Jinja 파일을 직접
주면 `url_for` 를 못 풀어 스타일시트를 못 읽는다 — 티켓 01·09·14 메모). 확인 폼은
세션 쿠키가 있어야 나오므로, 테스트 클라이언트로 한 번 렌더해 `web/static/` 아래에
떠 두고 같은 서버의 URL 로 스캔한다. 확인이 끝나면 지운다(커밋에 없다).

사용: `uv run python review/detect-snapshot-16.py`  (티켓 14 의 같은 스크립트 변형)
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.services.guest_service import issue_guest  # noqa: E402

STATIC = REPO_ROOT / "web" / "static"

app = create_app("testing")
with app.app_context():
    db.create_all()
    client = app.test_client()
    guest = issue_guest()
    db.session.commit()
    client.post("/api/v1/session/sync", headers={"Authorization": f"Bearer {guest.token}"})
    for language in ("ko", "en"):
        html = client.get(f"/account/delete?lang={language}").data.decode()
        # 스냅샷은 정적 파일로 열리므로 `/static/...` 절대 경로가 그대로 맞는다.
        (STATIC / f"_t16_form_{language}.html").write_text(html, encoding="utf-8")
        print(f"wrote web/static/_t16_form_{language}.html ({len(html)} bytes)")
