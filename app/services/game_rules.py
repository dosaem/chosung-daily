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
