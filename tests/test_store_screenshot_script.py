"""`scripts/store_screenshots.sh` 의 캡처 판정을 실제 bash 로 돌려 본다
(티켓 35, 수정 라운드 1).

최종 리뷰가 찾은 두 결함은 둘 다 "스크립트가 결과를 잘못 판정한다" 다 —
D-35-1(5장 중 1장만 찍히고 drive 가 죽어도 성공 처리), D-35-6(재촬영하면 과거
세트와 섞여 10장이 된다). 둘 다 `flutter drive` 를 실제로 돌리지 않고도 보이는데,
시뮬레이터가 필요한 부분(기기 찾기·부팅)과 판정 부분이 함수로 갈려 있어서다.

그래서 스크립트를 `STORE_SHOTS_LIB_ONLY=1` 로 **source** 해서 판정 함수만 가져오고,
`flutter` 를 shell 함수로 덮어 "몇 장을 만들고 어떤 코드로 끝났는지" 를 테스트가
정한다. 함수 사본을 테스트에 두지 않는 이유: 사본은 스크립트가 바뀌면 낡는다.
"""

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "store_screenshots.sh"

# 한 세트 = OVERRIDES §8 의 5장. 스크립트의 기대값과 같아야 한다.
SCENES = 5


def _bash(body: str) -> subprocess.CompletedProcess:
    """스크립트의 함수만 올린 bash 를 돌린다 — 메인 흐름(기기·에뮬레이터)은 건너뛴다."""
    script = f'STORE_SHOTS_LIB_ONLY=1 source "{SCRIPT}"\n{body}\n'
    return subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True, cwd=REPO_ROOT, check=False
    )


def _flutter_stub(made: int, exit_code: int) -> str:
    """`flutter drive` 대역. `$STORE_SHOT_DIR` 에 `made` 장을 만들고 `exit_code` 로 끝난다.

    받은 인자는 `$ARGS_LOG` 에 남긴다 — `--dart-define` 로 무엇을 넘겼는지 본다.
    """
    names = " ".join(f"ko_{index:02d}_scene.png" for index in range(1, made + 1))
    return f"""
flutter() {{
  [ -n "${{ARGS_LOG:-}}" ] && echo "$@" >> "$ARGS_LOG"
  for name in {names or '""'}; do
    [ -n "$name" ] && touch "$STORE_SHOT_DIR/$name"
  done
  return {exit_code}
}}
"""


def _seed(directory: Path, prefix: str, count: int = SCENES) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for index in range(1, count + 1):
        (directory / f"{prefix}_ko_{index:02d}_scene.png").write_text("old")


def _pngs(directory: Path) -> list[str]:
    return sorted(path.name for path in directory.glob("*.png"))


def test_the_script_can_be_sourced_for_its_capture_functions():
    """메인 흐름(시뮬레이터 생성·에뮬레이터 부팅)은 돌지 않아야 한다."""
    result = _bash('echo "loaded"; type -t capture; type -t replace_set')

    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["loaded", "function", "function"]


# --- D-35-1 부분 실패 -------------------------------------------------------


@pytest.mark.parametrize("made", [0, 1, SCENES - 1])
def test_capture_fails_when_the_drive_run_did_not_produce_the_whole_set(made, tmp_path):
    """D-35-1 재현: 1장만 찍히고 drive 가 죽어도 성공으로 넘어갔다.

    기대는 "실패 반환 + 기존 완성 세트 보존" 이다 — 성공으로 넘어가면 새 홈 1장과
    과거 4장이 섞인 세트가 스토어로 간다.
    """
    outdir = tmp_path / "out"
    _seed(outdir, "iphone69")

    result = _bash(
        f"""
        {_flutter_stub(made, 1)}
        capture_exit=0
        capture dummy-device ko "{outdir}" iphone69 || capture_exit=$?
        echo "capture_exit=$capture_exit"
        """
    )

    assert "capture_exit=0" not in result.stdout, "부분 실패를 성공으로 처리했다"
    assert _pngs(outdir) == [
        f"iphone69_ko_{index:02d}_scene.png" for index in range(1, SCENES + 1)
    ], "실패했는데 기존 세트를 건드렸다"


def test_capture_fails_when_the_drive_run_dies_after_a_full_set(tmp_path):
    """장면은 다 나왔지만 drive 가 0 이 아니면(단언 실패 등) 믿지 않는다."""
    outdir = tmp_path / "out"

    result = _bash(
        f"""
        {_flutter_stub(SCENES, 1)}
        capture_exit=0
        capture dummy-device ko "{outdir}" iphone69 || capture_exit=$?
        echo "capture_exit=$capture_exit"
        """
    )

    assert "capture_exit=0" not in result.stdout
    assert _pngs(outdir) == []


def test_capture_moves_the_whole_set_on_success(tmp_path):
    outdir = tmp_path / "out"

    result = _bash(
        f"""
        {_flutter_stub(SCENES, 0)}
        capture dummy-device ko "{outdir}" iphone69
        echo "capture_exit=$?"
        """
    )

    assert "capture_exit=0" in result.stdout, result.stderr
    assert _pngs(outdir) == [
        f"iphone69_ko_{index:02d}_scene.png" for index in range(1, SCENES + 1)
    ]


# --- D-35-6 세트 누적 -------------------------------------------------------


def test_capture_replaces_the_previous_phone_set_instead_of_piling_up(tmp_path):
    """D-35-6 재현: Play 폰 폴더에 대체 세트(`iphone69_*`)가 있는 채 Android 로
    다시 찍으면 이름이 달라 덮이지 않고 10장이 됐다 — Play 기기 유형별 8장 제한을
    넘는다. 그 폴더는 **한 기기 유형의 세트**라 세트 단위로 바꿔야 한다.
    """
    phone_dir = tmp_path / "phoneScreenshots"
    _seed(phone_dir, "iphone69")

    result = _bash(
        f"""
        {_flutter_stub(SCENES, 0)}
        capture dummy-device ko "{phone_dir}" android '*.png'
        echo "capture_exit=$?"
        """
    )

    assert "capture_exit=0" in result.stdout, result.stderr
    assert _pngs(phone_dir) == [
        f"android_ko_{index:02d}_scene.png" for index in range(1, SCENES + 1)
    ], f"세트가 누적됐다: {_pngs(phone_dir)}"


def test_capture_keeps_the_other_device_sets_in_the_shared_ios_folder(tmp_path):
    """반대로 iOS deliver 폴더는 기기 3종이 **같이** 산다(prefix 로 구분).
    6.9" 를 다시 찍어도 iPad 세트는 그대로 있어야 한다.
    """
    ios_dir = tmp_path / "screenshots" / "ko"
    _seed(ios_dir, "iphone69")
    _seed(ios_dir, "ipad13")

    result = _bash(
        f"""
        {_flutter_stub(SCENES, 0)}
        capture dummy-device ko "{ios_dir}" iphone69
        echo "capture_exit=$?"
        """
    )

    assert "capture_exit=0" in result.stdout, result.stderr
    assert len(_pngs(ios_dir)) == 2 * SCENES
    assert any(name.startswith("ipad13_") for name in _pngs(ios_dir))


def test_the_android_fallback_replaces_the_phone_set_too(tmp_path):
    """반대 방향 누적 — Android 로 찍어 둔 폴더에 대체 세트를 넣을 때도 세트
    단위로 바꾼다(D-35-6 "반대 방향 fallback 에서도 같은 누적").
    """
    phone_dir = tmp_path / "phoneScreenshots"
    _seed(phone_dir, "android")

    result = _bash(
        f"""
        {_flutter_stub(SCENES, 0)}
        fallback_phone_set dummy-device ko "{phone_dir}"
        echo "exit=$?"
        """
    )

    assert "exit=0" in result.stdout, result.stderr
    assert _pngs(phone_dir) == [
        f"androidui_ko_{index:02d}_scene.png" for index in range(1, SCENES + 1)
    ], f"세트가 누적됐다: {_pngs(phone_dir)}"


def test_the_android_fallback_shoots_the_android_composition(tmp_path):
    """D-35-5 재현(대체 경로): 에뮬레이터가 없을 때 iOS 세트를 그대로 복사하면
    iOS 에만 있는 ATT 안내 장이 Play 에 올라간다. 대체 세트도 **Android 구성**으로
    찍어야 한다 — 장면 쪽 스위치(`SHOT_IS_IOS`)를 넘기는지 본다.
    """
    phone_dir = tmp_path / "phoneScreenshots"
    args_log = tmp_path / "args.log"

    result = _bash(
        f"""
        export ARGS_LOG="{args_log}"
        {_flutter_stub(SCENES, 0)}
        fallback_phone_set dummy-device ko "{phone_dir}"
        echo "exit=$?"
        """
    )

    assert "exit=0" in result.stdout, result.stderr
    assert "--dart-define=SHOT_IS_IOS=false" in args_log.read_text()


def test_a_normal_capture_leaves_the_platform_to_the_device(tmp_path):
    """평소에는 스위치를 비워 둔다 — 기기가 Android 면 Android 구성이 나온다."""
    outdir = tmp_path / "out"
    args_log = tmp_path / "args.log"

    _bash(
        f"""
        export ARGS_LOG="{args_log}"
        {_flutter_stub(SCENES, 0)}
        capture dummy-device ko "{outdir}" android '*.png'
        """
    )

    assert args_log.read_text().rstrip("\n").endswith("--dart-define=SHOT_IS_IOS=")


def test_the_script_expects_exactly_the_scene_count_the_dart_file_defines():
    """스크립트의 기대 장수와 장면 정의가 갈리면 D-35-1 이 되돌아온다."""
    scenes = (REPO_ROOT / "mobile" / "integration_test" / "store_screenshot_scenes.dart").read_text(
        encoding="utf-8"
    )
    enum_body = scenes.split("enum StoreScene {", 1)[1].split("const StoreScene(", 1)[0]

    assert enum_body.count("('") == SCENES, "장면 수가 바뀌었다 — 스크립트 기대값도 같이 본다"
    assert f"EXPECTED_SHOTS:-{SCENES}" in SCRIPT.read_text(encoding="utf-8")
