"""임시 앱 아이콘/스플래시 이미지를 만든다 (티켓 22).

OVERRIDES §8 의 콘셉트 한 줄 — "다크 배경 #0F172A 에 brand 오렌지 타일 하나 +
흰 초성 ㅊ" — 을 그대로 그린다. 최종 아이콘·스토어 자산은 티켓 33 이 만든다.
생성물(`assets/icon/*.png`)은 커밋하고, 이 스크립트는 그 출처를 남기려고 둔다.

    python3 tool/make_placeholder_icon.py
    dart run flutter_launcher_icons
    dart run flutter_native_splash:create
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "icon"
SIZE = 1024
BACKGROUND = "#0F172A"
TILE = "#EA580C"
GLYPH_COLOR = "#FFFFFF"
GLYPH = "ㅊ"
KOREAN_FONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"


def draw_tile(image: Image.Image, tile_size: int) -> None:
    draw = ImageDraw.Draw(image)
    offset = (SIZE - tile_size) // 2
    box = (offset, offset, offset + tile_size, offset + tile_size)
    # 타일 모서리 8 / 크기 48 비율을 그대로 키운다.
    draw.rounded_rectangle(box, radius=round(tile_size * 8 / 48), fill=TILE)

    font = ImageFont.truetype(KOREAN_FONT, round(tile_size * 0.62))
    left, top, right, bottom = draw.textbbox((0, 0), GLYPH, font=font)
    draw.text(
        (
            (SIZE - (right - left)) / 2 - left,
            (SIZE - (bottom - top)) / 2 - top,
        ),
        GLYPH,
        font=font,
        fill=GLYPH_COLOR,
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    icon = Image.new("RGB", (SIZE, SIZE), BACKGROUND)
    draw_tile(icon, round(SIZE * 0.56))
    icon.save(OUT_DIR / "app_icon.png")

    # Android adaptive icon·스플래시용. 배경은 투명하고, 잘려도 되는 바깥 여백을
    # 남기려고 타일을 더 작게 그린다.
    foreground = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw_tile(foreground, round(SIZE * 0.42))
    foreground.save(OUT_DIR / "app_icon_foreground.png")


if __name__ == "__main__":
    main()
