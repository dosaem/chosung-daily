#!/usr/bin/env python3
"""올리기 전에 스크린샷 세트를 검사한다 (티켓 35).

fastlane 은 폴더에 있는 것을 **그대로** 올린다. 그래서 세트가 깨진 상태도 조용히
올라간다 — 캡처가 2장째 장면에서 죽어 1장만 바뀐 세트, 과거 세트와 섞여 10장이 된
폴더, 그리고 Android 에뮬레이터가 없던 날 iPhone 캡처를 그대로 복사해 둔 Play 폰
세트. 앞의 둘은 심사에서 막히고(iPad 세트가 모자라면 제출 자체가 안 된다), 마지막
것은 Play 가 요구하는 "실제 앱 경험" 이 아니다(iOS 에만 있는 ATT 안내 장이 들어
있다).

  python3 tool/verify_store_screenshots.py ios     # App Store (deliver)
  python3 tool/verify_store_screenshots.py play    # Play (supply)
  python3 tool/verify_store_screenshots.py both

실패하면 어떤 세트가 왜 틀렸는지 전부 찍고 1 로 끝난다. 찍는 쪽은
`scripts/store_screenshots.sh`, 올리는 쪽은 `.github/workflows/appstore-metadata.yml`
과 `android/fastlane/Fastfile` 의 `release` lane 이다.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

MOBILE = Path(__file__).resolve().parent.parent

# 한 세트 = OVERRIDES §8 의 5장(홈·결과·순위·내 기록·언어 선택).
EXPECTED = 5

# Play 는 기기 유형마다 최대 8장이다.
PLAY_MAX = 8

IOS_LOCALES = ("ko", "en-US")
PLAY_LOCALES = ("ko-KR", "en-US")

# iOS deliver 폴더는 기기 3종이 prefix 로 같이 산다. 6.5" 는 선택이다 — 없으면
# 애플이 6.9" 를 축소해서 쓴다. 있으면 온전해야 한다.
IOS_REQUIRED_PREFIXES = ("iphone69", "ipad13")
IOS_OPTIONAL_PREFIXES = ("iphone65",)

# 플랫폼으로 그림이 갈리는 장면. 온보딩은 iOS 에만 ATT 안내 장이 더 붙어서
# (`mobile/lib/onboarding/onboarding_pages.dart`) 페이지 표시 개수가 다르다. 나머지
# 네 장면(홈·결과·순위·내 기록)은 두 플랫폼이 같은 그림이라, iPhone 시뮬레이터에서
# 찍은 Android 구성 세트와 iOS 세트가 그 네 장은 **같은 바이트인 것이 정상**이다 —
# 그래서 "iPhone 복사본" 판정은 이 장면만 본다.
PLATFORM_DIVERGENT_SCENE = "06_language"


def _pngs(directory: Path, pattern: str = "*.png") -> list[Path]:
    return sorted(path for path in directory.glob(pattern) if path.is_file())


def _digests(paths: list[Path]) -> dict[str, Path]:
    return {hashlib.sha256(path.read_bytes()).hexdigest(): path for path in paths}


def check_ios(root: Path) -> list[str]:
    problems = []
    for locale in IOS_LOCALES:
        directory = root / "ios" / "fastlane" / "screenshots" / locale
        for prefix in IOS_REQUIRED_PREFIXES:
            shots = _pngs(directory, f"{prefix}_*.png")
            if len(shots) != EXPECTED:
                problems.append(
                    f"{directory}: {prefix} 세트가 {len(shots)}/{EXPECTED} 장이다"
                )
        for prefix in IOS_OPTIONAL_PREFIXES:
            shots = _pngs(directory, f"{prefix}_*.png")
            if shots and len(shots) != EXPECTED:
                problems.append(
                    f"{directory}: {prefix} 세트가 {len(shots)}/{EXPECTED} 장이다"
                    " (선택 기기지만 반쪽은 안 된다)"
                )
    return problems


def check_play(root: Path) -> list[str]:
    problems = []
    # iPhone 6.9" **온보딩** 캡처의 지문. Play 폰 세트에 이것과 바이트까지 같은
    # 파일이 있으면 그 세트는 iOS 구성(ATT 안내 1장 추가)을 담고 있다.
    iphone_onboarding: dict[str, Path] = {}
    for locale in IOS_LOCALES:
        directory = root / "ios" / "fastlane" / "screenshots" / locale
        iphone_onboarding.update(
            _digests(_pngs(directory, f"iphone69_*{PLATFORM_DIVERGENT_SCENE}*.png"))
        )

    for locale in PLAY_LOCALES:
        images = root / "android" / "fastlane" / "metadata" / "android" / locale / "images"
        for kind in ("phoneScreenshots", "tenInchScreenshots"):
            shots = _pngs(images / kind)
            if len(shots) != EXPECTED:
                problems.append(f"{images / kind}: {len(shots)}/{EXPECTED} 장이다")
            if len(shots) > PLAY_MAX:
                problems.append(
                    f"{images / kind}: {len(shots)} 장 —"
                    f" Play 기기 유형별 상한 {PLAY_MAX} 장을 넘는다"
                )

        # 태블릿 세트는 iPad 캡처를 그대로 쓰는 것이 맞다(같은 코드·같은 그림,
        # Play 는 폭·비율만 본다). 폰 세트는 아니다.
        for shot in _pngs(images / "phoneScreenshots"):
            source = iphone_onboarding.get(hashlib.sha256(shot.read_bytes()).hexdigest())
            if source is not None:
                problems.append(
                    f"{shot}: iOS 온보딩 캡처({source.name})와 바이트까지 같다 — Play 는"
                    " 실제 앱 경험을 요구하는데 이 그림에는 iOS 에만 있는 ATT 안내 장이"
                    " 들어 있다. AVD 로 다시 찍거나(권장) AVD 없이"
                    " scripts/store_screenshots.sh 를 돌려 Android 구성 세트를 만든다"
                )
    return problems


CHECKS = {"ios": check_ios, "play": check_play}


def main(argv: list[str]) -> int:
    program, *args = argv
    target = args[0] if args else "both"
    if target not in (*CHECKS, "both"):
        print(f"usage: {program} [ios|play|both] [mobile-root]", file=sys.stderr)
        return 2

    # 두 번째 인자는 `mobile/` 경로. 테스트가 임시 폴더를 넘긴다.
    root = Path(args[1]).resolve() if len(args) > 1 else MOBILE
    names = list(CHECKS) if target == "both" else [target]

    problems = []
    for name in names:
        problems += CHECKS[name](root)

    if problems:
        for problem in problems:
            print(f"::error::{problem}")
        print(f"스크린샷 세트 {len(problems)}건이 올릴 수 없는 상태다 (docs/RELEASE.md '35.')")
        return 1

    print(f"screenshots OK: {', '.join(names)} — 로케일마다 {EXPECTED} 장씩")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
