"""앱 아이콘·스플래시 마크 PNG 를 SVG 원본에서 만든다 (티켓 35).

원본은 `assets/icon/app_icon.svg` 한 장(OVERRIDES §8)이고, 이 스크립트는 그
`<rect>` 들을 **읽어서** 그린다 — 좌표·색을 두 벌로 적지 않으려고 SVG 를 파싱한다.
rasterizer(cairosvg·rsvg) 를 깔지 않는 이유도 같다: 타일 네 개짜리 도형이라
직접 그리는 쪽이 의존성 없이 결과가 고정된다.

    python3 tool/make_app_icon.py          # PIL(Pillow)은 시스템 python3 에 있다
    dart run flutter_launcher_icons
    dart run flutter_native_splash:create

만드는 것:
  assets/icon/app_icon.png             1024 불투명 — iOS 1024, Android 레거시 아이콘
  assets/icon/app_icon_foreground.png  1024 투명 — Android adaptive 전경, 스플래시 마크
  ../.scratch/store-launch/design/icon-30px.png  30x30 — "세 칸이 구분되는가" 확인용
  android/fastlane/metadata/android/*/images/icon.png          512 — Play 스토어 등록 아이콘
  android/fastlane/metadata/android/*/images/featureGraphic.png 1024x500 — Play 그래픽

Play 의 두 자산은 ko-KR·en-US 가 **같은 파일**이다 — 마크에 글자가 없어서
언어별로 갈릴 게 없다(OVERRIDES §8 "스토어는 앱당 아이콘 하나").
"""

import re
from pathlib import Path

from PIL import Image, ImageDraw

MOBILE_ROOT = Path(__file__).resolve().parent.parent
SVG_PATH = MOBILE_ROOT / "assets" / "icon" / "app_icon.svg"
ICON_DIR = MOBILE_ROOT / "assets" / "icon"
DESIGN_DIR = MOBILE_ROOT.parent / ".scratch" / "store-launch" / "design"

SIZE = 1024

# Android adaptive 아이콘은 108dp 캔버스의 안쪽 72dp(66%)만 반드시 보인다 —
# 전경 마크를 그 안에 넣어야 런처 마스크가 양끝 타일을 자르지 않는다.
FOREGROUND_MARK_RATIO = 0.62

# 스토어 목록에서 아이콘이 가장 작게 보이는 크기(티켓 35).
SMALL_RENDER = 30

# Play 스토어 등록 자산 규격. 아이콘 512x512, 그래픽 1024x500(둘 다 투명 금지).
PLAY_ICON = 512
PLAY_FEATURE_GRAPHIC = (1024, 500)
PLAY_FEATURE_MARK_RATIO = 0.42
PLAY_LOCALES = ("ko-KR", "en-US")

# 배경 1 + 타일 3. 다른 도형이 끼면 OVERRIDES §8 의 아이콘이 아니다.
RECT_COUNT = 4

RECT = re.compile(r"<rect\s([^>]*?)/>")
ATTR = re.compile(r'([a-z-]+)="([^"]*)"')


def parse_rects() -> list[dict[str, str]]:
    """SVG 의 `<rect>` 들을 문서 순서대로 돌려준다. 첫 칸이 배경이다."""
    svg = SVG_PATH.read_text(encoding="utf-8")
    rects = [dict(ATTR.findall(match.group(1))) for match in RECT.finditer(svg)]
    if len(rects) != RECT_COUNT:
        raise SystemExit(
            f"{SVG_PATH} 의 rect 가 {RECT_COUNT}개(배경+타일 3)가 아니다: {len(rects)}"
        )
    return rects


def draw_rect(
    draw: ImageDraw.ImageDraw,
    rect: dict[str, str],
    scale: float,
    dx: float,
    dy: float,
) -> None:
    x = float(rect["x"]) * scale + dx
    y = float(rect["y"]) * scale + dy
    box = (x, y, x + float(rect["width"]) * scale, y + float(rect["height"]) * scale)
    radius = float(rect["rx"]) * scale
    if radius > 0:
        draw.rounded_rectangle(box, radius=radius, fill=rect["fill"])
    else:
        draw.rectangle(box, fill=rect["fill"])


def mark_box(tiles: list[dict[str, str]]) -> tuple[float, float, float, float]:
    """타일 3칸을 감싸는 사각형 (x, y, 폭, 높이)."""
    left = min(float(tile["x"]) for tile in tiles)
    top = min(float(tile["y"]) for tile in tiles)
    right = max(float(tile["x"]) + float(tile["width"]) for tile in tiles)
    bottom = max(float(tile["y"]) + float(tile["height"]) for tile in tiles)
    return left, top, right - left, bottom - top


def main() -> None:
    rects = parse_rects()
    background, tiles = rects[0], rects[1:]
    viewbox = float(background["width"])

    # 1) 1024 아이콘 — 뷰박스를 그대로 확대한다(배경이 꽉 찬다).
    icon = Image.new("RGB", (SIZE, SIZE), background["fill"])
    icon_draw = ImageDraw.Draw(icon)
    for tile in tiles:
        draw_rect(icon_draw, tile, SIZE / viewbox, 0, 0)
    icon.save(ICON_DIR / "app_icon.png")

    # 2) adaptive 전경·스플래시 마크 — 배경 없이 마크만, 안전 영역 안에 가운데로.
    left, top, mark_width, mark_height = mark_box(tiles)
    scale = SIZE * FOREGROUND_MARK_RATIO / mark_width
    foreground = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    foreground_draw = ImageDraw.Draw(foreground)
    for tile in tiles:
        draw_rect(
            foreground_draw,
            tile,
            scale,
            (SIZE - mark_width * scale) / 2 - left * scale,
            (SIZE - mark_height * scale) / 2 - top * scale,
        )
    foreground.save(ICON_DIR / "app_icon_foreground.png")

    # 3) 30px 래스터 — 가운데 칸이 배경과 구분되는지 눈과 테스트로 확인한다.
    DESIGN_DIR.mkdir(parents=True, exist_ok=True)
    icon.resize((SMALL_RENDER, SMALL_RENDER), Image.LANCZOS).save(DESIGN_DIR / "icon-30px.png")

    # 4) Play 스토어 등록 아이콘·그래픽 — 같은 마크를 규격에 맞춰 다시 앉힌다.
    play_icon = icon.resize((PLAY_ICON, PLAY_ICON), Image.LANCZOS)
    feature_width, feature_height = PLAY_FEATURE_GRAPHIC
    feature = Image.new("RGB", PLAY_FEATURE_GRAPHIC, background["fill"])
    feature_draw = ImageDraw.Draw(feature)
    feature_scale = feature_width * PLAY_FEATURE_MARK_RATIO / mark_width
    for tile in tiles:
        draw_rect(
            feature_draw,
            tile,
            feature_scale,
            (feature_width - mark_width * feature_scale) / 2 - left * feature_scale,
            (feature_height - mark_height * feature_scale) / 2 - top * feature_scale,
        )
    for locale in PLAY_LOCALES:
        images = MOBILE_ROOT / "android" / "fastlane" / "metadata" / "android" / locale / "images"
        images.mkdir(parents=True, exist_ok=True)
        play_icon.save(images / "icon.png")
        feature.save(images / "featureGraphic.png")

    print(f"wrote {ICON_DIR}/app_icon.png, app_icon_foreground.png, {DESIGN_DIR}/icon-30px.png")
    locales = ",".join(PLAY_LOCALES)
    print(f"wrote android/.../metadata/android/{{{locales}}}/images/{{icon,featureGraphic}}.png")


if __name__ == "__main__":
    main()
