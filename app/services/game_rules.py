import unicodedata

from app.models.enums import PuzzleLanguage
from app.utils.mask import SEPARATOR_CHARS

MAX_ATTEMPTS = 5
HINT_AFTER_WRONG = 3


def compute_reveal(attempts_count: int, wrong_count: int, solved: bool) -> tuple[bool, bool]:
    """(finished, show_hint)를 계산한다.

    "3번째 오답 이후 힌트 공개"는 3번째 오답 응답 자체에 힌트를 포함하는 쪽으로
    해석했다 (wrong_count>=3이면 바로 show_hint=True) — "다음 시도부터"로 읽으면
    유저가 3번째 오답과 힌트 사이에 한 번 더 헛손질을 해야 해서, "오답을 하고 나면
    힌트가 나온다"는 문장의 자연스러운 흐름과 덜 맞다고 판단했다.

    finished면 정답을 보여주므로 힌트는 더 이상 의미가 없다 (show_hint=False).
    GET /puzzles/today 와 POST guesses 응답이 이 규칙을 공유한다.
    """
    finished = solved or attempts_count >= MAX_ATTEMPTS
    show_hint = (not finished) and wrong_count >= HINT_AFTER_WRONG
    return finished, show_hint


def summarize_attempts(attempts) -> tuple[bool, int]:
    """(solved, wrong_count)를 계산한다. puzzle_service/guess_service가 공유."""
    solved = any(a.is_correct for a in attempts)
    wrong_count = sum(1 for a in attempts if not a.is_correct)
    return solved, wrong_count


def day_result(attempts_count: int, solved: bool) -> str:
    """하루치 결과를 success|fail|in_progress|none 으로 분류한다 (기록 화면용).

    `GET /puzzles/today` 의 status 와 값이 겹치지만 한 가지가 다르다 — 거기선 아직
    한 번도 안 낸 상태가 "지금 풀고 있는 퍼즐"이라 `in_progress` 지만, 지난 날짜를
    돌아보는 기록 화면에서는 시도가 0개면 "미플레이"(`none`)다. 그래서
    get_today_puzzle_view 의 분기를 이 함수로 합치지 않았다.
    """
    if solved:
        return "success"
    if attempts_count == 0:
        return "none"
    if attempts_count >= MAX_ATTEMPTS:
        return "fail"
    return "in_progress"


def normalize_for_compare(language: PuzzleLanguage, text: str) -> str:
    """정답 비교에 쓰는 글자열 — 구분자(공백·하이픈)를 빼고, en 은 대문자로 맞춘다.

    가림(`mask`)이 구분자를 타일이 아닌 간격으로 보여주기 때문에(app/utils/mask.py),
    플레이어는 "harry potter"든 "harry-potter"든 "harrypotter"든 같은 뜻으로 친다.
    그래서 비교도 길이 검증도 `length`(= 구분자 제외 글자 수)와 같은 기준으로 한다.

    en 을 대문자로 맞추는 건 비교를 대소문자 무시로 만들면서(spec §A.2) `mask` 의
    보이는 타일(`_english_tile` 이 대문자로 통일)과 같은 모양을 쓰기 위해서다 —
    이 함수의 결과를 `Attempt.guess` 에 그대로 저장하므로, 이력을 복원한 보드의
    글자와 문제 타일의 글자가 한 화면에서 섞이지 않는다.
    """
    normalized = unicodedata.normalize("NFC", text.strip())
    letters = "".join(ch for ch in normalized if ch not in SEPARATOR_CHARS)
    return letters.upper() if language == PuzzleLanguage.EN else letters


def compare_letters(guess: str, answer: str) -> list[bool]:
    """글자별 피드백. 둘 다 `normalize_for_compare` 를 거친 글자열이어야 한다.

    길이는 항상 정답 기준(= 응답의 `length`)이다. 제출 경로는 길이를 미리 검증하니
    어차피 같지만, 시도 이력 복원은 구분자 규칙이 지금과 달랐던 옛 행도 그려야 해서
    짧은 guess 를 빈칸으로 채워 길이를 맞춘다.
    """
    padded = guess.ljust(len(answer))
    return [g == a for g, a in zip(padded, answer, strict=False)]
