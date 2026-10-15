"""KST 자정 근처면 0 이 아닌 코드로 끝난다 — E2E 스택이 시작 전에 부르는 가드.

서버는 KST 벽시계를 그대로 쓴다(앱에 테스트용 시계 주입구를 만들지 않기로 했다 —
코디네이터 결정 2026-10-15). 그래서 자정을 넘기며 돌면 실행 중에 "오늘" 이 바뀌어
연속 기록·퍼즐 날짜 검증이 거짓 실패한다. 한 판이 ~2분이라 여유를 10분으로 둔다.

셸 안에 파이썬 블록을 적지 않고 파일로 뺀 이유: `--now` 로 시각을 넣어 **테스트가
이 판정을 그대로 돌릴 수 있다**(tests/test_e2e_scripts.py). 셸 안에 두면 테스트가
같은 계산을 베껴 적어야 하고, 사본은 스크립트가 바뀌면 낡는다.
"""

import argparse
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
DEFAULT_MARGIN_SECONDS = 600


def seconds_from_midnight(now: datetime) -> float:
    """자정까지 남은 초와 자정 이후 지난 초 중 **작은** 쪽."""
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    to_next_midnight = (start_of_day + timedelta(days=1) - now).total_seconds()
    since_midnight = (now - start_of_day).total_seconds()
    return min(to_next_midnight, since_midnight)


def too_close_to_midnight(now: datetime, margin_seconds: int) -> bool:
    return seconds_from_midnight(now) < margin_seconds


def main() -> int:
    parser = argparse.ArgumentParser(description="KST 자정 근처면 비정상 종료한다")
    parser.add_argument("--now", help="판정할 시각(ISO). 없으면 현재 KST", default=None)
    parser.add_argument("--margin-seconds", type=int, default=DEFAULT_MARGIN_SECONDS)
    args = parser.parse_args()

    now = datetime.fromisoformat(args.now) if args.now else datetime.now(KST)
    if now.tzinfo is None:
        now = now.replace(tzinfo=KST)
    now = now.astimezone(KST)

    if too_close_to_midnight(now, args.margin_seconds):
        print(
            f"KST 자정 ±{args.margin_seconds // 60}분이다 "
            f"({now.strftime('%H:%M:%S')} KST) — 실행 중에 '오늘' 이 바뀐다.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
