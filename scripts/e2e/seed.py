"""E2E 스택의 시드 — 단어·오늘/내일 퍼즐·운영자 계정을 결정론적으로 심는다.

왜 결정론적인가: 브라우저 테스트가 "정답을 타이핑" 해야 하는데, 자정 배정
(`flask schedule-puzzles`)은 단어 풀에서 **무작위로** 고른다. 그러면 테스트가
정답을 알 수 없고, DB 를 훑어 정답을 읽는 코드가 테스트마다 생긴다. 그래서 시드가
오늘부터 5일치의 (날짜, 언어)별 단어를 못박고, 그 답을 manifest 파일 하나로
넘긴다 — 테스트는 manifest 만 읽는다.

멱등하다: 같은 DB 에 여러 번 돌려도 단어는 중복으로 안 들어가고(`import_word_rows`
가 (언어, 정답, 카테고리) 중복을 건너뛴다) 퍼즐 배정은 못박은 값으로 덮어쓴다.

단어 출처는 레포에 커밋된 두 파일뿐이다:
- ko: `data/seed_words.csv` (README "단어 시드" 가 쓰는 그 파일)
- en: `scripts/e2e/words_en.csv` (E2E 전용. `data/seed_words.csv` 에 language 열이
  없어서 전부 ko 라, en 퍼즐을 배정할 단어가 레포에 없다)
`data/word-candidates/` 는 읽지 않는다 — 실제 출시 정답이 테스트 로그로 샌다.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from app import create_app  # noqa: E402
from app.config import KST  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import (  # noqa: E402
    Account,
    DailyPuzzle,
    Guest,
    GuestStats,
    OAuthProvider,
    PuzzleLanguage,
    Word,
)
from app.services.puzzle_cache import invalidate_cached_puzzle  # noqa: E402
from app.services.puzzle_schedule_service import SCHEDULE_DAYS, schedule_puzzles  # noqa: E402
from app.services.word_service import seed_words_from_csv  # noqa: E402

KO_CSV = REPO_ROOT / "data" / "seed_words.csv"
EN_CSV = REPO_ROOT / "scripts" / "e2e" / "words_en.csv"

# 오늘(offset 0)부터 하루씩 못박을 단어. 둘째 날 것이 필요한 이유는 `advance_day.py`
# 가 날짜를 하루 내리면 그게 "오늘" 이 되기 때문이다(연속 기록 시나리오).
#
# 개수: 연속 기록 시나리오가 **한 판마다 하루를 넘긴다** — ko·en 2개 * 뷰포트 2개 = 4번이고
# k 번째 판은 `PINNED[k-1]`(1일차)과 `PINNED[k]`(2일차)를 쓰므로 언어마다 5개다. 날짜
# 시프트는 언어를 가리지 않으므로 두 언어가 같은 수여야 한다. 모자라면 마지막 판이
# "manifest 에 오늘 퍼즐이 없다" 로 깨진다 — 계약은
# `tests/test_e2e_scripts.py::test_pinned_words_cover_every_day_the_streak_scenario_advances`.
#
# ko 에 4글자(`어린왕자`)를 하나 섞어 둔다: 제출할 문자열을 적어둔 테스트는 정답 길이가
# 바뀌는 순간 서버의 길이 검증에 막혀 아무것도 검증하지 못한다(D-42-7). 길이가 섞여 있어야
# "정답에서 오답을 만든다" 가 지켜지는지 한 판으로 드러난다.
PINNED = {
    PuzzleLanguage.KO: ("컴퓨터", "자전거", "어린왕자", "냉장고", "지하철"),
    PuzzleLanguage.EN: ("apple", "school", "coffee", "window", "bicycle"),
}


def seed_words() -> dict[str, int]:
    created = {}
    for name, path in (("ko", KO_CSV), ("en", EN_CSV)):
        result = seed_words_from_csv(str(path))
        created[name] = result.created
        for line in result.skipped:
            print(f"  [{name}] 건너뜀: {line}")
    return created


def pin_puzzles(today):
    """`PINNED` 가 덮는 날들의 (날짜, 언어) 배정을 못박는다. 이미 다른 단어가 배정돼
    있으면 갈아끼우고, 그 날짜의 캐시도 지운다 — 캐시를 안 지우면 TTL 26시간 동안
    옛 단어가 계속 나간다(`puzzle_service` 가 cache-aside 다)."""
    pinned = []
    for language, answers in PINNED.items():
        for offset, answer in enumerate(answers):
            target_date = today + timedelta(days=offset)
            word = Word.query.filter_by(language=language, answer=answer).first()
            if word is None:
                raise SystemExit(
                    f"시드 CSV 에 {language.value} 단어 {answer!r} 가 없다 — "
                    "PINNED 와 CSV 가 어긋났다."
                )
            puzzle = DailyPuzzle.query.filter_by(
                puzzle_date=target_date, language=language
            ).first()
            if puzzle is None:
                puzzle = DailyPuzzle(
                    puzzle_date=target_date, language=language, word_id=word.id
                )
                db.session.add(puzzle)
            else:
                puzzle.word_id = word.id
            pinned.append((target_date, language, word))
    db.session.commit()
    for target_date, language, _ in pinned:
        invalidate_cached_puzzle(target_date, language)
    return pinned


def fill_schedule() -> dict[str, int]:
    """남은 30일을 평소 경로(`schedule_puzzles`)로 채운다. 운영자 배정표·잔량
    화면이 실제 운영과 같은 모양이어야 해서, 못박은 날들 말고는 그대로 둔다."""
    return {
        language.value: schedule_puzzles(language, days=SCHEDULE_DAYS)
        for language in PuzzleLanguage
    }


def ensure_admin(email: str, token: str) -> Guest:
    """운영자 판정을 통과하는 게스트 하나. `ADMIN_EMAILS` 에 이 이메일이 있다.

    실제 구글 OAuth 왕복은 하지 않는다(브리프: 실제 로그인 금지) — 대신 연결된
    계정이 **이미 있는** 상태를 만들어 두고, 브라우저는 '내 기록 > 복원' 에
    이 게스트의 백업 코드를 넣어 운영자 브라우저가 된다. `Guest.token` 이 평문
    UUID 라 시드가 값을 정할 수 있다.
    """
    guest = Guest.query.filter_by(token=token).first()
    if guest is None:
        guest = Guest(token=token, puzzle_language=PuzzleLanguage.KO)
        db.session.add(guest)
        db.session.flush()
        db.session.add(GuestStats(guest_id=guest.id))
    account = Account.query.filter_by(guest_id=guest.id).first()
    if account is None:
        db.session.add(
            Account(
                guest_id=guest.id,
                provider=OAuthProvider.GOOGLE,
                provider_user_id=f"e2e-admin-{token}",
                email=email,
            )
        )
    db.session.commit()
    return guest


def main() -> None:
    admin_email = os.environ["E2E_ADMIN_EMAIL"]
    admin_token = os.environ["E2E_ADMIN_TOKEN"]
    manifest_path = Path(os.environ["E2E_MANIFEST"])

    app = create_app("development")
    with app.app_context():
        today = datetime.now(KST).date()
        created = seed_words()
        print(f"단어 시드: ko {created['ko']}개 추가, en {created['en']}개 추가")
        pinned = pin_puzzles(today)
        scheduled = fill_schedule()
        print(f"퍼즐 배정: 못박음 {len(pinned)}건, 자동 배정 {scheduled}")
        admin = ensure_admin(admin_email, admin_token)
        print(f"운영자 게스트: id={admin.id} email={admin_email}")

        manifest = {
            "today": today.isoformat(),
            "admin": {"email": admin_email, "backup_code": admin_token},
            # (날짜, 언어) → 정답·힌트. 테스트는 "오늘" 을 자기가 다시 계산하지 않고
            # `puzzles[0]` 처럼 날짜 키로 찾는다.
            "puzzles": [
                {
                    "date": target_date.isoformat(),
                    "offset": (target_date - today).days,
                    "language": language.value,
                    "answer": word.answer,
                    "hint": word.hint,
                    "category": word.category.value,
                    "length": sum(1 for tile in word.mask if tile["t"] != "s"),
                }
                for target_date, language, word in pinned
            ],
        }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"manifest 기록: {manifest_path}")


if __name__ == "__main__":
    main()
