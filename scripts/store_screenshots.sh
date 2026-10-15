#!/bin/bash
# 스토어 스크린샷 캡처 (티켓 35). iOS 시뮬레이터 3종 + Android 에뮬레이터 1종에서
# `flutter drive` 로 5장(홈·결과·순위·내 기록·언어 선택)을 ko·en 각각 찍는다.
#
# 사용: ./scripts/store_screenshots.sh [ko|en|both]
#
# 결과물:
#   mobile/ios/fastlane/screenshots/{ko,en-US}/                        ← deliver 규격
#   mobile/android/fastlane/metadata/android/{ko-KR,en-US}/images/
#       phoneScreenshots/     ← Android 폰 (에뮬레이터)
#       tenInchScreenshots/   ← 태블릿 (iPad 13" 재사용 — 규격은 폭·비율만 본다)
#
# 규격(BASELINE `~/Code/Habitopia/scripts/store_screenshots.sh` 의 표를 그대로):
#   iPhone 6.9" 1320×2868 (iPhone 17 Pro Max)  — 필수
#   iPhone 6.5" 1242×2688 (iPhone 11 Pro Max)  — 선택(없으면 6.9" 를 애플이 축소)
#   iPad 13"    2064×2752 (iPad Pro 13-inch)   — iPad 지원 시 필수(없으면 심사 차단)
#   Android phone                              — Play 는 규격이 자유롭다
#
# iOS 기기가 없으면 `xcrun simctl create` 로 만든다. Android 는 AVD 가 있어야
# 하고(`$ANDROID_HOME/emulator -list-avds`), 없으면 그 단계만 건너뛴다.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

LOCALES="${1:-both}"
IPHONE_69_NAME="${IPHONE_69_NAME:-iPhone 17 Pro Max}"
IPHONE_65_NAME="${IPHONE_65_NAME:-iPhone 11 Pro Max}"
IPAD_NAME="${IPAD_NAME:-iPad Pro 13-inch (M5)}"
ANDROID_AVD="${ANDROID_AVD:-Medium_Phone_API_36.1}"
ANDROID_SDK="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
# 한 세트 = OVERRIDES §8 의 5장(홈·결과·순위·내 기록·언어 선택). 장면 정의는
# `mobile/integration_test/store_screenshot_scenes.dart` 의 `StoreScene` 이고,
# 둘이 갈리지 않는지 `tests/test_store_screenshot_script.py` 가 본다.
EXPECTED_SHOTS="${EXPECTED_SHOTS:-5}"

# 그 기기의 UDID. 없으면 같은 이름의 devicetype 으로 만들어 본다.
find_or_create_sim() {
  local name="$1"
  local udid
  udid=$(xcrun simctl list devices available -j | python3 -c "
import json,sys
devices = json.load(sys.stdin)['devices']
for runtime in devices.values():
    for device in runtime:
        if device['name'] == '''$name''':
            print(device['udid']); sys.exit()
")
  if [ -z "$udid" ]; then
    local devicetype
    devicetype=$(xcrun simctl list devicetypes -j | python3 -c "
import json,sys
for t in json.load(sys.stdin)['devicetypes']:
    if t['name'] == '''$name''':
        print(t['identifier']); sys.exit()
")
    if [ -z "$devicetype" ]; then
      echo "simulator not available: $name (xcrun simctl list devicetypes 로 확인)" >&2
      return 1
    fi
    local runtime
    runtime=$(xcrun simctl list runtimes -j | python3 -c "
import json,sys
runtimes = [r for r in json.load(sys.stdin)['runtimes'] if r['isAvailable'] and 'iOS' in r['name']]
print(runtimes[-1]['identifier'] if runtimes else '')
")
    udid=$(xcrun simctl create "$name" "$devicetype" "$runtime")
    echo "created simulator $name ($udid)" >&2
  fi
  echo "$udid"
}

boot_sim() {
  local udid="$1"
  xcrun simctl boot "$udid" 2>/dev/null || true
  # 스토어 규격 상태바 (9:41, 풀배터리, 풀시그널)
  xcrun simctl status_bar "$udid" override \
    --time "9:41" --batteryState charged --batteryLevel 100 \
    --cellularMode active --cellularBars 4 --wifiBars 3 2>/dev/null || true
}

# 한 기기 유형의 세트를 **통째로 바꾼다**. 결과 폴더에 과거 세트가 남으면 이름이
# 달라서 덮이지 않고 함께 올라가는데(Play 폰 폴더에 `iphone69_*` 대체 세트가 있는
# 채 `android_*` 로 다시 찍으면 10장), Play 는 기기 유형별로 최대 8장이고 심사에는
# 지금 화면이 아닌 그림이 섞인다.
replace_set() {
  local outdir="$1" glob="$2"
  mkdir -p "$outdir"
  find "$outdir" -maxdepth 1 -name "$glob" -delete
}

# 기기별 파일명 prefix 필수 — iPhone·iPad 가 같은 deliver 폴더를 쓰므로
# prefix 가 없으면 서로 덮어쓴다(deliver 는 해상도로 기기를 분류한다).
#
# 5번째 인자는 **이 세트가 소유한 파일 glob** 이다. iOS deliver 폴더는 기기 3종이
# 같이 사니 자기 prefix 만 바꾸고(기본값), 한 기기 유형만 쓰는 Play 폴더는
# `'*.png'` 를 넘겨 폴더째 바꾼다.
capture() {
  local device="$1" locale="$2" outdir="$3" prefix="$4" owned="${5:-${4}_*.png}"
  local tmpdir drive_exit=0
  tmpdir=$(mktemp -d)
  STORE_SHOT_DIR="$tmpdir" flutter drive \
    --driver=test_driver/integration_test.dart \
    --target=integration_test/store_screenshots_test.dart \
    -d "$device" \
    --dart-define=SHOT_LOCALE="$locale" \
    --dart-define=SHOT_IS_IOS="${STORE_SHOT_IS_IOS:-}" || drive_exit=$?
  # **종료 코드와 산출물 수를 둘 다 본다.** 이 함수는 `if ... ; then` 안에서도
  # 불리는데, 그 자리에서는 bash 가 `set -e` 를 꺼서 drive 가 죽어도 함수가 계속
  # 돈다 — 그래서 코드를 직접 받는다. 그리고 세트는 5장이 다 있어야 한다: 2장째
  # 장면에서 rail 단언이 깨지면 1장만 생기는데, "0장만 아니면 성공" 으로 보면
  # 새로 찍은 1장과 과거 4장이 섞인 세트가 스토어로 간다(실측 2026-10-15).
  local shots
  shots=$(find "$tmpdir" -name '*.png' | wc -l | tr -d ' ')
  if [ "$drive_exit" -ne 0 ] || [ "$shots" -ne "$EXPECTED_SHOTS" ]; then
    echo "캡처 실패: $prefix/$locale — drive=$drive_exit, $shots/$EXPECTED_SHOTS 장. 기존 세트는 그대로 둔다" >&2
    rm -rf "$tmpdir"
    return 1
  fi
  replace_set "$outdir" "$owned"
  for file in "$tmpdir"/*.png; do
    mv "$file" "$outdir/${prefix}_$(basename "$file")"
  done
  rm -rf "$tmpdir"
}

# Android 에뮬레이터가 없을 때의 Play 폰 세트. iPhone 시뮬레이터에서 찍지만
# **Android 구성**으로 찍는다(`SHOT_IS_IOS=false`) — iOS 세트를 그대로 복사하면
# iOS 만 있는 ATT 안내 장이 들어가 Play 에 실제와 다른 온보딩이 올라간다
# (최종 리뷰 D-35-5). Play 는 규격이 자유롭고 우리 캡처에는 OS 상태바가 없어서
# 해상도·기기 흔적은 문제가 되지 않는다.
fallback_phone_set() {
  local device="$1" locale="$2" phone_dir="$3"
  STORE_SHOT_IS_IOS=false capture "$device" "$locale" "$phone_dir" androidui '*.png'
}

android_device() {
  local serial
  serial=$("$ANDROID_SDK/platform-tools/adb" devices | awk '/emulator-/ {print $1; exit}')
  if [ -n "$serial" ]; then
    echo "$serial"
    return 0
  fi
  if ! "$ANDROID_SDK/emulator/emulator" -list-avds | grep -qx "$ANDROID_AVD"; then
    return 1
  fi
  "$ANDROID_SDK/emulator/emulator" -avd "$ANDROID_AVD" -no-snapshot-save -no-audio >/dev/null 2>&1 &
  "$ANDROID_SDK/platform-tools/adb" wait-for-device >&2
  # 부팅이 끝나기 전에 설치하면 install 이 깨진다. `sys.boot_completed` 는 **이르다** —
  # 그 플래그가 1 이 된 뒤에도 패키지 매니저가 아직 안 떠서 `adb install` 이
  # "Can't find service: package" 로 죽는다(실측 2026-10-15). 서비스 자체를 묻는다.
  until [ "$("$ANDROID_SDK/platform-tools/adb" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; do
    sleep 3
  done
  until "$ANDROID_SDK/platform-tools/adb" shell service check package 2>/dev/null | grep -q "found"; do
    sleep 3
  done
  "$ANDROID_SDK/platform-tools/adb" devices | awk '/emulator-/ {print $1; exit}'
}

run_locale() {
  local locale="$1"
  # deliver(App Store) 폴더명은 ko / en-US, supply(Play) 는 ko-KR / en-US.
  local deliver_locale supply_locale
  if [ "$locale" = "ko" ]; then
    deliver_locale="ko"; supply_locale="ko-KR"
  else
    deliver_locale="en-US"; supply_locale="en-US"
  fi
  local ios_dir="ios/fastlane/screenshots/$deliver_locale"
  local play_dir="android/fastlane/metadata/android/$supply_locale/images"

  echo "===== iPhone 6.9\" ($locale) ====="
  local udid iphone69_udid
  udid=$(find_or_create_sim "$IPHONE_69_NAME" | tail -1)
  iphone69_udid="$udid"
  boot_sim "$udid"
  capture "$udid" "$locale" "$ios_dir" iphone69

  echo "===== iPhone 6.5\" ($locale) ====="
  if udid=$(find_or_create_sim "$IPHONE_65_NAME" | tail -1); then
    boot_sim "$udid"
    capture "$udid" "$locale" "$ios_dir" iphone65
  else
    echo "건너뜀 — 6.5\" 세트가 없으면 애플이 6.9\" 를 축소해 쓴다" >&2
  fi

  echo "===== iPad 13\" ($locale) — 심사 제출 필수 ====="
  udid=$(find_or_create_sim "$IPAD_NAME" | tail -1)
  boot_sim "$udid"
  capture "$udid" "$locale" "$ios_dir" ipad13

  # Play 태블릿 세트는 iPad 13" 캡처를 그대로 쓴다 — Play 는 폭·비율만 보고,
  # 태블릿 레이아웃(rail + 2열)은 같은 코드라 그림이 같다.
  replace_set "$play_dir/tenInchScreenshots" '*.png'
  cp "$ios_dir"/ipad13_*.png "$play_dir/tenInchScreenshots/"

  echo "===== Android phone ($locale) ====="
  # 에뮬레이터가 없거나(AVD 미생성) 설치가 실패해도(에뮬레이터 /data 가 가득 차면
  # "Requested internal only, but not enough space" 로 죽는다) Play 등록은 막히면
  # 안 된다 — BASELINE(`~/Code/Habitopia/scripts/store_screenshots.sh`)처럼 iPhone
  # 시뮬레이터로 대신 찍는다. 다만 **Android 구성**으로 찍는다(`fallback_phone_set`).
  # 이 폴더는 **폰 한 기기 유형**의 세트라 폴더째 바꾼다(`'*.png'`).
  local serial
  if serial=$(android_device) && \
     capture "$serial" "$locale" "$play_dir/phoneScreenshots" android '*.png'; then
    :
  else
    echo "Android 캡처 실패/건너뜀 — iPhone 6.9\" 시뮬레이터에서 Android 구성으로 찍는다" >&2
    fallback_phone_set "$iphone69_udid" "$locale" "$play_dir/phoneScreenshots"
  fi
}

# 판정 함수(`capture`·`replace_set`·`fallback_phone_set`)만 가져다 쓰는 테스트는
# 여기서 멈춘다 — 아래는 시뮬레이터·에뮬레이터가 있어야 도는 메인 흐름이다
# (`tests/test_store_screenshot_script.py`).
if [ "${STORE_SHOTS_LIB_ONLY:-0}" = "1" ]; then
  # source 된 경우는 return, 실수로 실행한 경우는 exit (둘 다 성공으로 끝낸다).
  return 0 2>/dev/null || exit 0
fi

cd "$SCRIPT_DIR/../mobile"

if [ "$LOCALES" = "both" ]; then
  run_locale ko
  run_locale en
else
  run_locale "$LOCALES"
fi

echo ""
echo "완료. 결과:"
find ios/fastlane/screenshots android/fastlane/metadata/android/*/images -name '*.png' | sort
echo ""
echo "다음 단계: gh workflow run appstore-metadata.yml (스크린샷 포함 업로드)"
