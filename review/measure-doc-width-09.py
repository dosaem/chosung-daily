"""실제 브라우저에서 `.doc` 외곽 폭·패딩을 재는 D-09-3 재현 스크립트.

개발 서버의 렌더 HTML + 실제 tokens.css·legal.css 를 inline 하고(외부 CDN·Jinja 링크
해석을 피한다), 폭을 고정한 iframe 안에서 열어 헤드리스 Chrome 으로 computed style 을
읽는다. iframe 을 쓰는 이유: macOS 의 헤드리스 Chrome 은 창 폭을 500px 밑으로 못 줄여서
모바일 미디어 쿼리(≤480)가 창 크기로는 재현되지 않는다.
"""

import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1])
WIDTHS = [int(w) for w in sys.argv[2:]] or [375, 480, 481, 768]
BASE = "http://127.0.0.1:5099"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

HOST = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0}iframe{border:0;display:block}</style></head><body>
<iframe id="f" src="PAGE" style="width:WIDTHpx;height:1200px"></iframe>
<script>
document.getElementById('f').addEventListener('load', function () {
  var w = this.contentWindow, d = w.document.querySelector('.doc');
  var cs = w.getComputedStyle(d);
  var pre = document.createElement('pre');
  pre.textContent = 'MEASURE=' + JSON.stringify({
    viewport: w.innerWidth,
    docOuterWidth: d.getBoundingClientRect().width,
    boxSizing: cs.boxSizing,
    paddingTop: cs.paddingTop,
    paddingLeft: cs.paddingLeft,
    paddingRight: cs.paddingRight,
    maxWidth: cs.maxWidth,
    horizontalOverflow: w.document.documentElement.scrollWidth > w.innerWidth
  });
  document.body.appendChild(pre);
});
</script></body></html>"""

tokens = (REPO / "web/static/tokens.css").read_text(encoding="utf-8")
legal = (REPO / "web/static/legal.css").read_text(encoding="utf-8")

for name, url in [
    ("privacy-ko", "/privacy?lang=ko"),
    ("privacy-en", "/privacy?lang=en"),
    ("terms-ko", "/terms?lang=ko"),
    ("terms-en", "/terms?lang=en"),
]:
    html = urllib.request.urlopen(BASE + url).read().decode()
    html = re.sub(r'\s*<link rel="stylesheet"[^>]*>', "", html)
    html = html.replace("</head>", f"<style>\n{tokens}\n{legal}\n</style></head>")
    page = OUT / f"{name}.html"
    page.write_text(html, encoding="utf-8")
    for width in WIDTHS:
        host = OUT / f"host-{name}-{width}.html"
        body = HOST.replace("PAGE", page.name).replace("WIDTH", str(width))
        host.write_text(body, encoding="utf-8")
        proc = subprocess.run(
            [
                CHROME,
                "--headless=new",
                "--disable-gpu",
                "--no-first-run",
                "--allow-file-access-from-files",
                "--window-size=1200,1400",
                "--virtual-time-budget=4000",
                f"--user-data-dir={OUT}/profile",
                "--dump-dom",
                host.as_uri(),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        m = re.search(r"MEASURE=(\{.*?\})", proc.stdout)
        got = json.loads(m.group(1)) if m else {"error": proc.stderr[-200:]}
        print(f"{name} @{width}px  {json.dumps(got, ensure_ascii=False)}")
