"""en 스토어 스크린샷 OCR 검사 (티켓 35 리뷰 전 보정).

- 'Guest #xxxx' 접두사가 그림에 영어로 찍혔는가
- en 복수형이 1 일 때 단수인가 ("1 try"/"1 day"/"1 puzzle")
- 한글이 한 글자도 없는가

`1 puzzles` 를 그냥 부분문자열로 찾으면 "41 puzzles" 의 꼬리가 걸린다 —
앞에 숫자가 없을 때만 센다.
"""
import pathlib
import re
import subprocess
import sys

BAD = [re.compile(r"(?<![0-9])1 " + w) for w in ("tries", "days", "puzzles")]
HANGUL = re.compile(r"[가-힣ㄱ-ㆎ]")

fail = 0
for path in sorted(pathlib.Path(sys.argv[1]).glob(sys.argv[2])):
    out = subprocess.run(
        ["tesseract", str(path), "stdout", "--psm", "6"],
        capture_output=True, text=True, check=True,
    ).stdout
    hangul = HANGUL.findall(out)
    bad = [m.group(0) for p in BAD for m in [p.search(out)] if m]
    guests = sorted(line.strip() for line in out.split("\n") if "Guest" in line)
    plural = sorted({m.group(0) for m in re.finditer(r"\d+ (?:try|tries|days?|puzzles?)", out)})
    print(f"--- {path.name}")
    if guests:
        for line in guests:
            print(f"    {line}")
    print(f"    수량 문구: {plural or '없음'}")
    print(f"    한글 {len(hangul)}자 · 잘못된 단수/복수 {bad or '없음'}")
    fail += len(hangul) + len(bad)

print(f"\n== 한글 + 잘못된 복수형 합계: {fail} ==")
sys.exit(1 if fail else 0)
