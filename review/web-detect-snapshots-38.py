"""티켓 38: `impeccable detect` 에 먹일 리더보드 스냅샷을 만든다.

실제 템플릿(`web/templates/index.html`) + 실제 CSS(tokens.css·style.css) + 실제
번들이 그린 행 마크업을 합친다. 행은 번들을 node 로 돌려 꺼냈다(render_rows.mjs)
— 손으로 다시 적으면 그건 번들이 그리는 화면이 아니다.

쓰는 법:
  uv run python review/web-detect-snapshots-38.py <출력 디렉터리>
  (cd <출력 디렉터리> && python3 -m http.server 9438 &)
  ~/.impeccable/bin/0.1.14/impeccable detect http://127.0.0.1:9438/{ko,en}-{light,dark}.html
"""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = pathlib.Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

from app import create_app  # noqa: E402
from app.utils.ui_strings import UI_STRINGS  # noqa: E402

STATIC = ROOT / "web" / "static"
HERE = pathlib.Path(__file__).resolve().parent

app = create_app("testing")
app.config["WTF_CSRF_ENABLED"] = False

for language in ("ko", "en"):
    with app.test_client() as client:
        html = client.get(
            "/", headers={"Accept-Language": f"{language};q=0.9"}
        ).get_data(as_text=True)
    assert f'<html lang="{language}"' in html, language

    rendered = subprocess.run(
        [
            "node",
            str(HERE / "web-detect-rows-38.mjs"),
            json.dumps(UI_STRINGS[language]),
            language,
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    rows = json.loads(rendered.stdout)

    # 바깥 요청(CDN 폰트·정적 파일)을 없앤다 — detect 는 로컬 파일만 본다.
    html = re.sub(r'<link\s+rel="stylesheet"\s+href="https://[^"]*"\s*/?>', "", html)
    def inline(match: "re.Match[str]") -> str:
        css = (STATIC / f"{match.group(1)}.css").read_text(encoding="utf-8")
        return f"<style>{css}</style>"

    html = re.sub(
        r'<link rel="stylesheet" href="[^"]*(tokens|style)\.css[^"]*" />', inline, html
    )
    html = re.sub(r"<script[^>]*></script>", "", html)

    # 스켈레톤을 걷고 순위 섹션을 펼친다(번들의 init() 이 하는 일).
    html = html.replace(
        '<section id="leaderboard-section" class="section hidden"',
        '<section id="leaderboard-section" class="section"',
    )
    html = html.replace('<section id="today-section" class="section"',
                        '<section id="today-section" class="section hidden"')
    html = html.replace('aria-pressed="false">\n        ' + UI_STRINGS[language]["nav_leaderboard"],
                        'aria-pressed="true">\n        ' + UI_STRINGS[language]["nav_leaderboard"])

    html = html.replace('<p id="my-rank" class="my-rank"></p>',
                        f'<p id="my-rank" class="my-rank">{rows["myRank"]}</p>')
    entries_open = '<ol id="leaderboard-entries" class="leaderboard-entries">'
    html = html.replace(
        f"{entries_open}</ol>", f"{entries_open}{rows['entries']}</ol>"
    )
    html = html.replace('<ul id="today-stats" class="today-stats"></ul>',
                        f'<ul id="today-stats" class="today-stats">{rows["stats"]}</ul>')

    assert rows["entries"] in html, language
    assert rows["stats"] in html, language

    for mode in ("light", "dark"):
        page = html
        if mode == "dark":
            # 다크는 토큰만으로 따라온다(OVERRIDES §9, 수동 토글 없음). detect 에는
            # 색상 모드 옵션이 없으니 토큰의 다크 선언을 조건 없이 켜서 한 파일로 본다 —
            # 보는 색은 우리 다크 토큰 그대로다(브라우저 반전이 아니다).
            page = page.replace(
                "@media (prefers-color-scheme: dark) {", "@media all {", 1
            )
            assert "@media all {" in page
        (OUT / f"{language}-{mode}.html").write_text(page, encoding="utf-8")

print("\n".join(sorted(p.name for p in OUT.glob("*.html"))))
