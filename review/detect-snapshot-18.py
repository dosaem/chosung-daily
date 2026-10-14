"""`impeccable detect` 용 스냅샷: 메인 페이지의 **숨은 상태**와 **다크 토큰** 판.

detect 는 보이는 것만 보고, `prefers-color-scheme` 을 바꿔 주지도 않는다. 그런데 티켓
18 이 만든 것 중 상당수는 JS 가 켜야 보이거나(결과·앱 CTA·상태 카드·오프라인 배너·
다른 섹션) 다크에서만 색이 바뀐다. 그래서 떠 있는 서버의 `/` 를 그대로 받아
`web/static/` 아래에 네 벌로 떠 둔다 — 라이트/다크 2종 x ko/en 2종.

- `hidden` 클래스를 떼어 숨은 상태를 전부 펼친다(한 화면에 겹쳐 보이지만, 이건 보기
  좋으라고 만든 화면이 아니라 색·여백을 재는 판이다).
- 타일은 JS 가 그리므로 샘플 보드 한 줄을 끼워 넣는다 — `tile-correct`/`tile-wrong`/
  `tile-empty` 의 대비를 실제 클래스로 재려면 글자가 있어야 한다.
- 다크 판은 `tokens.css` 의 `prefers-color-scheme: dark` 블록을 **그 파일에서 읽어**
  `:root` 에 다시 올린다(값을 여기 베껴 적으면 토큰이 바뀔 때 조용히 어긋난다).

사용: `uv run python review/detect-snapshot-18.py` → 같은 서버의 URL 로 detect.
확인이 끝나면 `--clean` 으로 지운다(커밋에 없다). 티켓 14·16 의 같은 스크립트 변형.
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app import create_app  # noqa: E402

STATIC = REPO_ROOT / "web" / "static"
TOKENS_CSS = STATIC / "tokens.css"

# 스토어 등록 후의 상태도 같이 본다 — 배지·Smart App Banner 가 비면 안 그려지므로,
# 값이 없으면 그 부분을 영영 스캔하지 못한다. 실제 ID 가 아니라 자리를 채우는 값이다.
STORE_CONFIG = {
    "STORE_URL_IOS": "https://apps.apple.com/app/id0000000000",
    "STORE_URL_ANDROID": "https://play.google.com/store/apps/details?id=com.example.app",
    "APP_STORE_ID": "0000000000",
    # 사업자 정보도 "등록 후" 를 본다. 실제 값이 아니라 길이만 비슷한 자리표시자다.
    "LEGAL_BUSINESS_NAME": "오늘의 초성",
    "LEGAL_REPRESENTATIVE": "운영자",
    "LEGAL_BUSINESS_ADDRESS": "서울특별시 ○○구",
}

# JS 가 그리는 보드 한 줄. 클래스 이름은 web/static/app.js 의 renderAttemptRow 와 같다.
SAMPLE_BOARD = (
    '<div class="tile-row">'
    '<span class="tile tile-correct">사</span>'
    '<span class="tile tile-wrong">자</span>'
    "</div>"
)
SAMPLE_MASK = '<span class="tile tile-revealed">ㅅ</span><span class="tile tile-empty"></span>'


def dark_root_block() -> str:
    """`tokens.css` 의 다크 재정의를 `:root` 규칙 하나로 뽑아낸다."""
    css = TOKENS_CSS.read_text(encoding="utf-8")
    inside = css.split("@media (prefers-color-scheme: dark)", 1)[1]
    body = inside.split(":root {", 1)[1].split("\n  }", 1)[0]
    return f":root {{{body}\n}}"


def snapshot(html: str, *, dark: bool) -> str:
    # 숨은 상태를 전부 펼친다. 템플릿의 `class="... hidden"` 만 지운다.
    html = re.sub(r'(\sclass="[^"]*?)\s*\bhidden\b', r"\1", html)
    for empty, filled in (
        ('class="board"></section>', f'class="board">{SAMPLE_BOARD}</section>'),
        ('class="tile-row mask-row"></div>', f'class="tile-row mask-row">{SAMPLE_MASK}</div>'),
    ):
        html = html.replace(empty, filled)
    if dark:
        html = html.replace("</head>", f"<style>{dark_root_block()}</style>\n</head>")
    return html


def main() -> None:
    if "--clean" in sys.argv:
        for path in STATIC.glob("_t18_*.html"):
            path.unlink()
            print(f"removed {path.relative_to(REPO_ROOT)}")
        return

    app = create_app("testing")
    app.config.update(STORE_CONFIG)
    client = app.test_client()
    for language in ("ko", "en"):
        html = client.get(f"/?lang={language}").data.decode()
        for mode in ("light", "dark"):
            target = STATIC / f"_t18_{language}_{mode}.html"
            target.write_text(snapshot(html, dark=mode == "dark"), encoding="utf-8")
            print(f"wrote {target.relative_to(REPO_ROOT)} ({target.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
