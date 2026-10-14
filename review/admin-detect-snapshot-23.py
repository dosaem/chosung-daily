"""티켓 23 의 운영자 화면(배정표·잔량·토글·책 검색)을 `impeccable detect` 가 볼 수
있는 HTML 스냅샷으로 뽑는다.

방식은 티켓 15 의 `review/admin-detect-snapshot-15.py` 와 같다: 운영자 세션을
태운 Flask 테스트 클라이언트로 **실제 응답 HTML** 을 받고, 링크된 스타일시트만
같은 디렉터리의 복사본으로 바꿔 저장한다. 그 디렉터리를 정적 서버로 띄우면
detect 가 로그인 없이 같은 HTML·CSS 를 실제 브라우저로 본다(템플릿을 그냥
스캔하면 Jinja `url_for` 를 못 풀어 CSS 를 못 읽는다).

구글 책 검색은 **가짜 응답**으로 대체한다 — 스냅샷을 뽑을 때 외부 API 를 부르지
않는다.

사용법:
    uv run python review/admin-detect-snapshot-23.py <출력 디렉터리>
"""

import json
import re
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app import create_app  # noqa: E402
from app.clients import google_books  # noqa: E402
from app.config import KST  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import (  # noqa: E402
    Account,
    Attempt,
    DailyPuzzle,
    OAuthProvider,
    PuzzleLanguage,
    Word,
    WordCategory,
)
from app.services.guest_service import issue_guest  # noqa: E402

ADMIN_EMAIL = "snapshot-admin@example.com"
OK = 200
STYLESHEETS = ("tokens.css", "admin.css")

GOOGLE_PAYLOAD = {
    "items": [
        {
            "volumeInfo": {
                "title": "The Hobbit",
                "authors": ["J. R. R. Tolkien"],
                "publisher": "Houghton Mifflin",
                "industryIdentifiers": [
                    {"type": "ISBN_13", "identifier": "9780395071229"}
                ],
            }
        },
        {
            "volumeInfo": {
                "title": "The Lord of the Rings: The Fellowship of the Ring",
                "authors": ["J. R. R. Tolkien", "Alan Lee"],
                "publisher": "Houghton Mifflin Harcourt",
            }
        },
        {"volumeInfo": {"title": "Dune"}},
    ]
}


def _fake_google(payload):
    def _get(url, **_kwargs):
        response = requests.Response()
        response.status_code = OK
        response.url = url
        response._content = json.dumps(payload).encode()
        response.headers["Content-Type"] = "application/json"
        return response

    return _get


def _seed(low_stock: bool) -> None:
    """배정표에 보일 상태를 만든다: 오늘(시도 있음)·내일 배정 + 빈 날짜 + 잔량.

    `low_stock=False` 면 두 언어 모두 14일치를 넘겨 경고가 꺼진 화면이 된다.
    """
    today = datetime.now(KST).date()
    pool = 2 if low_stock else 20

    ko_words = [
        Word(
            answer=answer,
            language=PuzzleLanguage.KO,
            category=category,
            hint=hint,
        )
        for answer, category, hint in [
            ("지하철역", WordCategory.GENERAL, "지하철을 타고 내리는 곳"),
            ("데미안", WordCategory.BOOK_TITLE, "헤르만 헤세의 성장 소설"),
        ]
    ]
    ko_words += [
        Word(
            answer=f"단어{i}",
            language=PuzzleLanguage.KO,
            category=WordCategory.GENERAL,
            hint=f"채워 넣은 잔량 {i}",
        )
        for i in range(pool)
    ]
    en_words = [
        Word(
            answer=answer,
            language=PuzzleLanguage.EN,
            category=WordCategory.GENERAL,
            hint=hint,
        )
        for answer, hint in [("mountain range", "a line of connected peaks")]
    ]
    en_words += [
        Word(
            answer=f"word{i}",
            language=PuzzleLanguage.EN,
            category=WordCategory.GENERAL,
            hint=f"filler {i}",
        )
        for i in range(pool)
    ]
    db.session.add_all(ko_words + en_words)
    db.session.flush()

    today_puzzle = DailyPuzzle(
        puzzle_date=today, language=PuzzleLanguage.KO, word_id=ko_words[0].id
    )
    db.session.add_all(
        [
            today_puzzle,
            DailyPuzzle(
                puzzle_date=today + timedelta(days=1),
                language=PuzzleLanguage.KO,
                word_id=ko_words[1].id,
            ),
            DailyPuzzle(
                puzzle_date=today,
                language=PuzzleLanguage.EN,
                word_id=en_words[0].id,
            ),
        ]
    )
    db.session.flush()

    # 오늘은 이미 시도가 있어서 "교체 불가" 로 그려진다.
    guest = issue_guest()
    db.session.add(
        Attempt(
            guest_id=guest.id,
            puzzle_id=today_puzzle.id,
            guess="오답",
            is_correct=False,
            attempt_no=1,
        )
    )
    db.session.commit()


def _localize(html: str) -> str:
    """`/static/x.css?v=123` 링크를 같은 디렉터리의 `x.css` 로 바꾼다."""
    for name in STYLESHEETS:
        html = re.sub(rf"/static/{name}\?v=\d+", name, html)
    return html


def _save(out_dir: Path, filename: str, response, label: str) -> None:
    if response.status_code != OK:
        raise SystemExit(f"{label} → {response.status_code}")
    (out_dir / filename).write_text(
        _localize(response.get_data(as_text=True)), encoding="utf-8"
    )
    print(f"{filename} ← {label}")


def _login(app):
    guest = issue_guest()
    db.session.add(
        Account(
            guest_id=guest.id,
            provider=OAuthProvider.GOOGLE,
            provider_user_id="snapshot",
            email=ADMIN_EMAIL,
        )
    )
    db.session.commit()

    client = app.test_client()
    client.post(
        "/api/v1/session/sync", headers={"Authorization": f"Bearer {guest.token}"}
    )
    return client


def _csrf(client, path: str) -> str:
    html = client.get(path).get_data(as_text=True)
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def main(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    app = create_app("testing")
    app.config["ADMIN_EMAILS"] = (ADMIN_EMAIL,)
    google_books.requests.get = _fake_google(GOOGLE_PAYLOAD)

    today = datetime.now(KST).date()
    tomorrow = (today + timedelta(days=1)).isoformat()
    empty_day = (today + timedelta(days=7)).isoformat()

    with app.app_context():
        db.drop_all()
        db.create_all()
        _seed(low_stock=True)
        client = _login(app)

        _save(
            out_dir,
            "schedule_low.html",
            client.get("/admin/schedule"),
            "/admin/schedule (잔량 경고)",
        )
        _save(
            out_dir,
            "schedule_en.html",
            client.get("/admin/schedule?language=en"),
            "/admin/schedule?language=en",
        )
        _save(
            out_dir,
            "schedule_replace.html",
            client.get(f"/admin/schedule/{tomorrow}/replace?language=ko"),
            f"/admin/schedule/{tomorrow}/replace",
        )
        _save(
            out_dir,
            "schedule_replace_empty.html",
            client.get(f"/admin/schedule/{empty_day}/replace?language=ko&q=없는단어"),
            "교체 화면 (검색 결과 없음)",
        )
        _save(out_dir, "settings.html", client.get("/admin/settings"), "/admin/settings")

        # 거부된 저장(사유 + 운영자가 적은 값 유지) 화면.
        token = _csrf(client, "/admin/settings")
        _save(
            out_dir,
            "settings_error.html",
            client.post(
                "/admin/settings",
                data={
                    "csrf_token": token,
                    "maintenance_enabled": "on",
                    "maintenance_message": "",
                    "min_app_version_ios": "v1.4",
                    "min_app_version_android": "1.0.0",
                },
            ),
            "POST /admin/settings (거부)",
        )

        _save(
            out_dir,
            "books.html",
            client.get("/admin/books?q=tolkien"),
            "/admin/books?q=tolkien (결과 3건)",
        )
        _save(out_dir, "books_form.html", client.get("/admin/books"), "/admin/books (검색 전)")

        google_books.requests.get = _fake_google({"items": []})
        _save(
            out_dir,
            "books_empty.html",
            client.get("/admin/books?q=zzzzz"),
            "/admin/books (결과 없음)",
        )

        # 잔량이 넉넉한 화면(경고 테두리가 꺼진 상태)도 같이 본다.
        db.session.remove()
        db.drop_all()
        db.create_all()
        _seed(low_stock=False)
        client = _login(app)
        _save(
            out_dir,
            "schedule_ok.html",
            client.get("/admin/schedule"),
            "/admin/schedule (잔량 정상)",
        )

        db.session.remove()
        db.drop_all()

    for name in STYLESHEETS:
        shutil.copy(REPO_ROOT / "web" / "static" / name, out_dir / name)
        print(f"{name} (복사)")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
