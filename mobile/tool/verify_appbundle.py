"""방금 만든 AAB 가 업로드해도 되는 산출물인지 검사한다 (티켓 34).

`flutter build appbundle --release` 는 `debugSymbolLevel=FULL` 일 때 스트립
오탐으로 exit 1 을 주면서도 AAB 는 정상 생성한다. 그래서 배포 경로는 종료 코드를
삼키는데, 그러면 진짜 빌드 실패도 같이 삼켜진다 — 삼킨 만큼 산출물로 직접
확인해야 한다. Actions 의 AAB 스텝과 수동 `fastlane beta/release` 가 같은 검사를
쓰도록 스크립트 하나로 둔다.

    python3 tool/verify_appbundle.py build/app/outputs/bundle/release/app-release.aab

검사 항목:
  1. 열리는 zip 이고 base 모듈의 AndroidManifest 가 있다 (= 온전한 AAB).
  2. 배포 lib(`base/lib/*/libapp.so`)가 있고 전부 스트립돼 있다
     (= exit 1 이 오탐이었고 스트립이 진짜 실패한 게 아니다).

호출한 쪽이 빌드 전에 대상 파일을 지워야 한다. 이 스크립트는 "이번 빌드가
만들었는지"를 알 수 없고 파일 내용만 본다.
"""

import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

# 인자는 AAB 경로 하나 — `argv` 는 스크립트 이름까지 둘이다.
EXPECTED_ARGV = 2
USAGE_EXIT = 2
MANIFEST = "base/manifest/AndroidManifest.xml"
DELIVERED_LIB = re.compile(r"^base/lib/[^/]+/libapp\.so$")


def delivered_libs(bundle: zipfile.ZipFile) -> list[str]:
    return [name for name in bundle.namelist() if DELIVERED_LIB.match(name)]


def unstripped(bundle: zipfile.ZipFile, name: str) -> bool:
    """`file` 이 ELF 섹션 헤더에서 심볼 테이블을 찾으면 "not stripped" 라고 한다."""
    with tempfile.NamedTemporaryFile(suffix=".so") as handle:
        handle.write(bundle.read(name))
        handle.flush()
        described = subprocess.run(
            ["file", "-b", handle.name], capture_output=True, text=True, check=True
        ).stdout
    return "not stripped" in described


def verify(path: Path) -> list[str]:
    if not path.exists():
        return [f"{path} 가 없다 — 이번 빌드가 AAB 를 만들지 못했다"]

    try:
        bundle = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        return [f"{path} 를 zip 으로 열 수 없다 ({exc}) — 빌드가 중간에 끊겼다"]

    with bundle:
        if MANIFEST not in bundle.namelist():
            return [f"{MANIFEST} 가 없다 — AAB 가 온전하지 않다"]

        libs = delivered_libs(bundle)
        if not libs:
            return ["base/lib/*/libapp.so 가 없다 — Dart AOT 산출물이 빠졌다"]

        return [
            f"{name} 이 스트립되지 않았다 — 스트립 오탐이 아니라 실제 실패다"
            for name in sorted(libs)
            if unstripped(bundle, name)
        ]


def main(argv: list[str]) -> int:
    if len(argv) != EXPECTED_ARGV:
        print(f"usage: {argv[0]} <path-to-aab>", file=sys.stderr)
        return USAGE_EXIT

    problems = verify(Path(argv[1]))
    for problem in problems:
        print(f"AAB 검사 실패: {problem}", file=sys.stderr)
    if problems:
        return 1

    print(f"AAB 검사 통과: {argv[1]} (manifest 있음, 배포 lib 스트립됨)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
