"""운영자 페이지를 `impeccable detect` 로 검사할 수 있는 HTML 스냅샷으로 뽑는다.

detect 는 URL 을 받으면 실제 브라우저로 페이지를 열어 CSS 까지 파싱하는데(티켓 09
증거), 운영자 페이지는 로그인 세션이 필요해서 detect 가 직접 열 수 없다. 그래서
여기서 **운영자 세션을 태운 Flask 테스트 클라이언트로 실제 응답을 받아** 저장하고,
링크된 스타일시트만 같은 디렉터리의 복사본으로 바꾼다. 그 디렉터리를 정적 서버로
띄우면 detect 가 로그인 없이 같은 HTML·CSS 를 본다.

사용법:
    uv run python review/admin-detect-snapshot-15.py <출력 디렉터리>
"""

import io
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Account, OAuthProvider, PuzzleLanguage, Word, WordCategory  # noqa: E402
from app.services.guest_service import issue_guest  # noqa: E402

ADMIN_EMAIL = "snapshot-admin@example.com"
OK = 200
STYLESHEETS = ("tokens.css", "admin.css")

# 어떤 URL 을 어떤 파일 이름으로 저장할지. 상태가 다른 화면(빈 목록·결과 표)도 같이
# 뽑는다 — 운영자가 실제로 보는 화면은 대부분 "결과가 있는" 쪽이다.
PAGES = {
    "words.html": "/admin/",
    "words_filtered.html": "/admin/?language=ko&q=%EC%82%AC",
    "words_empty.html": "/admin/?q=%EC%97%86%EB%8A%94%EB%8B%A8%EC%96%B4",
    "word_new.html": "/admin/words/new",
    "word_edit.html": None,  # 아래에서 단어 id 를 붙인다
    "import.html": "/admin/words/import",
}


def _seed_words() -> int:
    words = [
        ("사과", PuzzleLanguage.KO, WordCategory.GENERAL, "빨간 과일"),
        ("지하철역", PuzzleLanguage.KO, WordCategory.GENERAL, "타는 곳"),
        ("데미안", PuzzleLanguage.KO, WordCategory.BOOK_TITLE, "헤르만 헤세"),
        ("apple", PuzzleLanguage.EN, WordCategory.GENERAL, "red fruit"),
        ("mountain range", PuzzleLanguage.EN, WordCategory.GENERAL, "a line of peaks"),
    ]
    first_id = None
    for answer, language, category, hint in words:
        word = Word(answer=answer, language=language, category=category, hint=hint)
        db.session.add(word)
        db.session.flush()
        first_id = first_id or word.id
    db.session.commit()
    return first_id


def _localize(html: str) -> str:
    """`/static/x.css?v=123` 링크를 같은 디렉터리의 `x.css` 로 바꾼다."""
    for name in STYLESHEETS:
        html = re.sub(rf"/static/{name}\?v=\d+", name, html)
    return html


def main(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    app = create_app("testing")
    app.config["ADMIN_EMAILS"] = (ADMIN_EMAIL,)
    with app.app_context():
        db.drop_all()
        db.create_all()
        word_id = _seed_words()

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

        pages = dict(PAGES)
        pages["word_edit.html"] = f"/admin/words/{word_id}/edit"
        for filename, path in pages.items():
            res = client.get(path)
            if res.status_code != OK:
                raise SystemExit(f"{path} → {res.status_code}")
            (out_dir / filename).write_text(
                _localize(res.get_data(as_text=True)), encoding="utf-8"
            )
            print(f"{filename} ← {path}")

        # 업로드 결과 표는 POST 응답에만 있다 — 운영자가 실제로 오래 보는 화면이라
        # 같이 뽑는다. 폼 토큰은 렌더된 페이지에서 꺼낸다(1회용).
        token = re.search(
            r'name="csrf_token" value="([^"]+)"',
            client.get("/admin/words/import").get_data(as_text=True),
        ).group(1)
        body = (
            "language,category,answer,hint\n"
            "ko,general,사과,이미 있는 단어\n"
            "ko,general,기차역,타는 곳\n"
            "fr,general,pomme,fruit\n"
        ).encode()
        res = client.post(
            "/admin/words/import",
            data={"csrf_token": token, "file": (io.BytesIO(body), "words.csv")},
            content_type="multipart/form-data",
        )
        if res.status_code != OK:
            raise SystemExit(f"업로드 결과 → {res.status_code}")
        (out_dir / "import_result.html").write_text(
            _localize(res.get_data(as_text=True)), encoding="utf-8"
        )
        print("import_result.html ← POST /admin/words/import")

        db.session.remove()
        db.drop_all()

    for name in STYLESHEETS:
        shutil.copy(REPO_ROOT / "web" / "static" / name, out_dir / name)
        print(f"{name} (복사)")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
