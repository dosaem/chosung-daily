"""단어 후보 생성 규칙 — 정답·힌트가 퍼즐로 나갈 수 있는 모양인지 보는 순수 함수.

원래 `scripts/check_word_csv.py` 가 들고 있던 규칙을 그대로 옮겼다(티켓 LLM 출제
1단계). 이유: LLM 이 만든 후보(`word_generation_service`)와 사람이 만든 CSV 가 **같은
규칙**을 통과해야 한다 — 규칙이 스크립트에만 있으면 서비스는 느슨한 사본을 갖게 된다.

이 모듈은 DB·네트워크·파일을 보지 않는다. 형식 검증(`parse_word_input`)을 통과한
`WordInput` 을 받아 사람이 읽을 사유 목록을 돌려줄 뿐이다. 사유 문구는 스크립트
시절과 글자 하나 다르지 않다 — 스크립트 테스트가 그 문구를 고정하고 있고, 운영자가
어드민 승인 화면에서 같은 문구로 탈락 사유를 본다.
"""

import re
from dataclasses import dataclass

from app.models import PuzzleLanguage
from app.services.word_service import WordInput

# 언어별 정답 길이. ko 는 음절 수, en 은 구분자를 포함한 글자 수다.
KO_ANSWER_RANGE = (2, 5)
EN_ANSWER_RANGE = (2, 12)

# 힌트는 타일 아래 한 줄로 들어간다 — 컬럼 상한(200자)보다 짧게 잡는다.
HINT_MAX_LENGTH = 60

# en 정답에 쓸 수 있는 글자와 구분자(공백·하이픈 합쳐 최대 1개 = 두 단어까지).
EN_ANSWER_PATTERN = re.compile(r"^[a-z -]+$")
EN_SEPARATORS = " -"
EN_MAX_SEPARATORS = 1

# 모음을 가리고 내는 문제라, 모음이 절반을 넘으면 남는 자음 뼈대가 단서가 안 된다
# (`aeon` → `_ _ N`). 가림 규칙은 app/utils/mask.py 와 같은 모음 집합을 본다.
EN_VOWELS = frozenset("aeiou")
EN_MAX_VOWEL_RATIO = 0.5

# 힌트에 정답이 새는지 볼 때, 두 단어 정답의 각 낱말은 3글자 이상만 본다 —
# `a`·`of` 같은 조각은 어느 힌트에나 들어 있어서 사유가 될 수 없다.
EN_HINT_PART_MIN_LENGTH = 3

KO_SYLLABLE_PATTERN = re.compile(r"^[가-힣]+$")

DuplicateKey = tuple[str, str, str]


@dataclass(frozen=True)
class Violation:
    """규칙을 어긴 행 하나. `line` 은 CSV 줄 번호(헤더가 1행)다 — 운영자가
    스프레드시트에서 그 줄을 바로 찾아 지울 수 있어야 한다."""

    line: int
    reason: str


def candidate_reasons(parsed: WordInput) -> list[str]:
    """정답·힌트 규칙 위반 사유. 중복은 보지 않는다(호출부가 자기 집합으로 본다)."""
    return _answer_reasons(parsed) + _hint_reasons(parsed)


def duplicate_reasons(
    parsed: WordInput,
    seen: dict[DuplicateKey, int],
    known_keys: set[DuplicateKey],
    line: int,
    known_label: str,
) -> list[str]:
    """같은 묶음 안 중복과, 이미 있는 단어(`known_keys`)와의 중복.

    `seen` 은 호출부가 들고 다니는 "이 묶음에서 먼저 본 정답 → 줄 번호" 다. 중복이
    아니면 여기서 `seen` 에 넣는다 — 먼저 나온 행이 살아남고 뒤가 탈락한다.
    `known_label` 은 사유에 붙는 출처 이름(CSV 파일 경로, "단어 풀" 등)이다.
    """
    key = parsed.duplicate_key
    if key in seen:
        return [f"같은 파일 안에서 중복된 정답입니다 ({seen[key]}행과 같음)."]
    if key in known_keys:
        return [f"{known_label} 에 이미 있는 정답입니다."]
    seen[key] = line
    return []


def _answer_reasons(parsed: WordInput) -> list[str]:
    if parsed.language is PuzzleLanguage.EN:
        return _en_answer_reasons(parsed.answer)
    return _ko_answer_reasons(parsed.answer)


def _ko_answer_reasons(answer: str) -> list[str]:
    reasons = []
    if not KO_SYLLABLE_PATTERN.match(answer):
        reasons.append("정답에 완성형 한글이 아닌 글자가 있습니다 (공백·숫자·기호·영문 금지).")
    low, high = KO_ANSWER_RANGE
    if not low <= len(answer) <= high:
        reasons.append(f"정답이 {len(answer)}글자입니다 (ko 는 {low}~{high}글자).")
    return reasons


def _en_answer_reasons(answer: str) -> list[str]:
    reasons = []
    if not EN_ANSWER_PATTERN.match(answer):
        reasons.append("정답은 소문자 a-z 와 공백·하이픈만 쓸 수 있습니다.")
    low, high = EN_ANSWER_RANGE
    if not low <= len(answer) <= high:
        reasons.append(f"정답이 {len(answer)}자입니다 (en 은 {low}~{high}자).")

    separators = sum(1 for ch in answer if ch in EN_SEPARATORS)
    if separators > EN_MAX_SEPARATORS:
        reasons.append(f"구분자(공백·하이픈)가 {separators}개입니다 (최대 1개 = 두 단어까지).")

    letters = [ch for ch in answer.lower() if ch not in EN_SEPARATORS]
    vowels = sum(1 for ch in letters if ch in EN_VOWELS)
    if letters and vowels / len(letters) > EN_MAX_VOWEL_RATIO:
        reasons.append(
            f"모음이 {vowels}/{len(letters)} 입니다 — 모음을 가리면 자음 뼈대가 안 남습니다."
        )
    return reasons


def _hint_reasons(parsed: WordInput) -> list[str]:
    hint = parsed.hint
    reasons = []
    if len(hint) > HINT_MAX_LENGTH:
        reasons.append(f"힌트가 {len(hint)}자입니다 (1~{HINT_MAX_LENGTH}자).")
    if "\n" in hint or "\r" in hint:
        reasons.append("힌트는 한 줄이어야 합니다.")
    if any(ch in hint for ch in '",'):
        reasons.append("힌트에 따옴표·쉼표를 쓸 수 없습니다.")

    if parsed.language is PuzzleLanguage.EN:
        reasons.extend(_en_hint_leak_reasons(parsed.answer, hint))
    else:
        reasons.extend(_ko_hint_leak_reasons(parsed.answer, hint))
    return reasons


def _ko_hint_leak_reasons(answer: str, hint: str) -> list[str]:
    """힌트가 정답 음절을 하나라도 쓰면 초성이 그대로 보인다 — `책상` 의 힌트에
    `책` 이 있으면 ㅊ ㅅ 두 칸 중 한 칸이 공짜다."""
    # 한글 음절만 본다 — 정답에 섞인 공백·기호는 어느 힌트에나 있어서 사유가
    # 안 되고, 그건 정답 쪽 규칙(`_ko_answer_reasons`)이 따로 잡는다.
    shared = sorted(
        {
            syllable
            for syllable in answer
            if KO_SYLLABLE_PATTERN.match(syllable) and syllable in hint
        }
    )
    if not shared:
        return []
    return [f"힌트에 정답 음절이 들어 있습니다: {' '.join(shared)}"]


def _en_hint_leak_reasons(answer: str, hint: str) -> list[str]:
    """힌트에 정답 단어(또는 복수형)가 낱말로 들어 있으면 문제가 아니라 답이다."""
    words = " ".join(re.findall(r"[a-z]+", hint.lower()))
    phrase = answer.replace("-", " ")
    targets = {phrase} | {part for part in phrase.split() if len(part) >= EN_HINT_PART_MIN_LENGTH}

    for target in sorted(targets):
        for form in _plural_forms(target):
            if re.search(rf"\b{re.escape(form)}\b", words):
                return [f"힌트에 정답 단어가 들어 있습니다: {form}"]
    return []


def _plural_forms(word: str) -> set[str]:
    forms = {word, f"{word}s"}
    if word.endswith("y"):
        forms.add(f"{word[:-1]}ies")
    if word.endswith(("s", "sh", "ch", "x", "z")):
        forms.add(f"{word}es")
    return forms
