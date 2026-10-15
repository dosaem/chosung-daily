"""티켓 46 이 건드린 화면을 `impeccable detect` 가 볼 수 있는 HTML 로 뽑는다.

두 묶음이다.

1. **플레이어 웹 "내 기록" 섹션** — 백업 패널이 열린 상태(D-42-1 복사 버튼,
   D-42-2 백업 코드 칸의 `aria-label`). 티켓 38 의 `web-detect-snapshots-38.py` 와
   같은 방식으로 실제 응답 HTML 에 CSS 를 인라인하고, 번들의 `init()` 이 하는
   섹션 토글·패널 열기를 마크업으로 대신한다.
2. **운영자 표 5개** — 티켓 46 이 전부 `.admin-table-scroll` 로 감쌌다(D-42-4).
   티켓 23 의 `admin-detect-snapshot-23.py` 가 이미 배정표·교체·책 검색을 뽑으므로,
   여기서는 그 스크립트가 다루지 않는 **단어 목록**과 **CSV 업로드 결과**만 더한다.

사용법:
    uv run python review/detect-snapshots-46.py <출력 디렉터리>
    (cd <출력 디렉터리> && python3 -m http.server 9446 &)
    ~/.impeccable/bin/0.1.14/impeccable detect http://127.0.0.1:9446/<파일>.html
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
from app.models import (  # noqa: E402
    Account,
    OAuthProvider,
    PuzzleLanguage,
    Word,
    WordCategory,
)
from app.services.guest_service import issue_guest  # noqa: E402

STATIC = REPO_ROOT / "web" / "static"
PLAYER_STYLESHEETS = ("tokens.css", "style.css")
ADMIN_STYLESHEETS = ("tokens.css", "admin.css")
ADMIN_EMAIL = "snapshot46-admin@example.com"
OK = 200
# 백업 코드는 평문 UUID 다 — 스냅샷에 들어가므로 실제 토큰이 아닌 고정 값을 쓴다.
SAMPLE_TOKEN = "00000000-0000-4000-8000-000000000046"


def _player_pages(app, out_dir: Path) -> None:
    """`/` 를 ko/en x light/dark 로. "내 기록" 섹션과 백업 패널을 펼친 상태다."""
    for language in ("ko", "en"):
        with app.test_client() as client:
            html = client.get(
                "/", headers={"Accept-Language": f"{language};q=0.9"}
            ).get_data(as_text=True)
        assert f'<html lang="{language}"' in html, language

        # 바깥 요청(CDN 폰트)·번들을 없애고 CSS 를 인라인한다 — detect 는 로컬만 본다.
        html = re.sub(r'<link\s+rel="stylesheet"\s+href="https://[^"]*"\s*/?>', "", html)

        def inline(match: "re.Match[str]") -> str:
            css = (STATIC / f"{match.group(1)}.css").read_text(encoding="utf-8")
            return f"<style>{css}</style>"

        html = re.sub(
            r'<link rel="stylesheet" href="[^"]*(tokens|style)\.css[^"]*" />', inline, html
        )
        html = re.sub(r"<script[^>]*></script>", "", html)

        # 번들의 init() 이 하는 일을 마크업으로: "내 기록" 섹션을 펼치고 백업 패널을 연다.
        html = html.replace(
            '<section id="records-section" class="section hidden"',
            '<section id="records-section" class="section"',
        )
        html = html.replace(
            '<section id="today-section" class="section"',
            '<section id="today-section" class="section hidden"',
        )
        html = html.replace(
            '<div id="backup-panel" class="panel hidden">',
            '<div id="backup-panel" class="panel">',
        )
        html = html.replace(
            '<input id="token-display" type="text" readonly',
            f'<input id="token-display" type="text" value="{SAMPLE_TOKEN}" readonly',
        )
        assert 'id="backup-panel" class="panel">' in html, language

        for mode in ("light", "dark"):
            page = html
            if mode == "dark":
                # detect 에 색상 모드 옵션이 없다 — 토큰의 다크 선언을 조건 없이 켠다
                # (티켓 38 과 같은 방식. 브라우저 반전이 아니라 우리 다크 토큰이다).
                page = page.replace(
                    "@media (prefers-color-scheme: dark) {", "@media all {", 1
                )
                assert "@media all {" in page
            (out_dir / f"records-{language}-{mode}.html").write_text(page, encoding="utf-8")

    for name in PLAYER_STYLESHEETS:
        shutil.copy(STATIC / name, out_dir / name)


def _admin_pages(app, out_dir: Path) -> None:
    """티켓 23 스냅샷이 안 다루는 운영자 표 둘: 단어 목록 · CSV 업로드 결과."""
    with app.app_context():
        db.drop_all()
        db.create_all()

        db.session.add_all(
            [
                Word(
                    answer=answer,
                    language=language,
                    category=category,
                    hint=hint,
                )
                for answer, language, category, hint in [
                    ("지하철역", PuzzleLanguage.KO, WordCategory.GENERAL,
                     "지하철을 타고 내리는 곳"),
                    ("데미안", PuzzleLanguage.KO, WordCategory.BOOK_TITLE,
                     "헤르만 헤세의 성장 소설"),
                    ("mountain range", PuzzleLanguage.EN, WordCategory.GENERAL,
                     "a line of connected peaks"),
                ]
            ]
        )
        guest = issue_guest()
        db.session.add(
            Account(
                guest_id=guest.id,
                provider=OAuthProvider.GOOGLE,
                provider_user_id="snapshot46",
                email=ADMIN_EMAIL,
            )
        )
        db.session.commit()

        client = app.test_client()
        client.post(
            "/api/v1/session/sync", headers={"Authorization": f"Bearer {guest.token}"}
        )

        _save(out_dir, "admin-words.html", client.get("/admin/"))

        csrf = re.search(
            r'name="csrf_token" value="([^"]+)"',
            client.get("/admin/words/import").get_data(as_text=True),
        ).group(1)
        csv_body = (
            "answer,language,category,hint\n"
            "바다거북,ko,general,등딱지가 있는 바다 동물\n"
            "하늘공원,ko,general,서울의 공원\n"
            "지하철역,ko,general,중복이라 건너뛴다\n"
            "물고기,ko,없는카테고리,카테고리가 틀렸다\n"
        ).encode()
        _save(
            out_dir,
            "admin-import.html",
            client.post(
                "/admin/words/import",
                data={
                    "csrf_token": csrf,
                    "file": (io.BytesIO(csv_body), "words.csv"),
                },
                content_type="multipart/form-data",
            ),
        )

        db.session.remove()
        db.drop_all()

    for name in ADMIN_STYLESHEETS:
        shutil.copy(STATIC / name, out_dir / name)


def _save(out_dir: Path, filename: str, response) -> None:
    if response.status_code != OK:
        raise SystemExit(f"{filename} → {response.status_code}")
    html = response.get_data(as_text=True)
    for name in set(PLAYER_STYLESHEETS) | set(ADMIN_STYLESHEETS):
        html = re.sub(rf"/static/{name}\?v=\d+", name, html)
    (out_dir / filename).write_text(html, encoding="utf-8")
    print(filename)


def main(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    app = create_app("testing")
    app.config["ADMIN_EMAILS"] = (ADMIN_EMAIL,)
    app.config["WTF_CSRF_ENABLED"] = False

    _player_pages(app, out_dir)
    _admin_pages(app, out_dir)
    print("\n".join(sorted(p.name for p in out_dir.glob("*.html"))))


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
