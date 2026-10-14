"""웹 게임 화면(`/`)의 UI 문자열 사전.

문구의 주인은 서버다. 템플릿은 `{{ t.key }}` 로, JS 는 페이지에 인라인으로 심긴
`#ui-strings` JSON 에서 같은 사전을 읽는다 — 문구가 템플릿·JS 두 곳에 흩어지지
않고, 사전 자체를 pytest 로 검증할 수 있다(README "17. UI 문자열 사전은 서버가
고른다").

어느 언어로 그릴지는 `app/utils/ui_language.py` 의 `resolve_ui_language` 가 정한다
(법적 문서 페이지와 같은 규칙). 법적 문서는 본문이 길어서 언어마다 템플릿 파일을
따로 두지만, 게임 화면은 짧은 문구 수십 개라 사전 한 장이 맞다.

**UI 언어는 퍼즐 언어와 별개다**(`CONTEXT.md` "UI 언어"). UI 언어는 기기 설정,
퍼즐 언어는 플레이어가 칩으로 고르는 문제의 언어다.
"""

# 자리표시자는 `{name}` 꼴이다. JS 의 format()(web/static/app.js)과 같은 규칙이고,
# 양쪽 언어에 같은 이름이 있어야 한다(tests/test_ui_strings.py).
UI_STRINGS: dict[str, dict[str, str]] = {
    "ko": {
        # 머리말·계정
        "app_title": "오늘의 초성",
        "streak_loading": "-",
        "streak_summary": "연속 {current}일 · 최고 {max}일 · 누적 {solved}문제",
        "streak_load_failed": "기록을 불러오지 못했어요.",
        "login_google": "구글로 로그인",
        "login_apple": "Apple로 로그인",
        "provider_google": "구글",
        "provider_apple": "Apple",
        "linked_account": "✅ {provider} 계정으로 로그인됨",
        "linked_account_with_email": "✅ {provider} 계정으로 로그인됨 ({email})",
        # 백업 코드
        "backup_open": "내 기록 백업",
        "restore_open": "다른 기기 기록 불러오기",
        "backup_desc": "이 코드를 저장해두면 다른 기기에서도 같은 기록으로 이어할 수 있어요.",
        "restore_desc": "백업해둔 코드를 붙여넣으면 그 기록을 이 기기로 가져와요.",
        "backup_code_placeholder": "백업 코드 붙여넣기",
        "copy": "복사",
        "copied": "복사했어요!",
        "restore_submit": "불러오기",
        "restore_invalid_code": "올바르지 않은 백업 코드예요. 다시 확인해주세요.",
        # 퍼즐 언어 칩
        "puzzle_language_label": "퍼즐 언어",
        "puzzle_language_ko": "한국어",
        "puzzle_language_en": "English",
        "puzzle_language_failed": "퍼즐 언어를 바꾸지 못했어요.",
        # 퍼즐·플레이
        "category_general": "일반 단어",
        "category_book_title": "책 제목",
        "length_caption": "{length}글자",
        "attempts_left": "남은 기회 {left}/{max}",
        "hint": "힌트: {hint}",
        "guess_placeholder": "정답을 입력하세요",
        "submit": "제출",
        "guest_issue_failed": "게스트 발급에 실패했어요. 잠시 뒤 다시 시도해주세요.",
        "puzzle_load_failed": "오늘의 퍼즐을 불러오지 못했어요.",
        "puzzle_changed": "새 퍼즐이 있어요",
        # 계정 삭제(티켓 14)가 /?deleted=1 로 돌려보낸 뒤, 옛 토큰을 버리고 띄우는 안내.
        "account_deleted": "계정과 기록을 삭제했어요. 새 기록으로 다시 시작합니다.",
        "generic_error": "오류가 발생했어요.",
        # API 오류 code 별 문구. 서버 응답의 `message` 는 한국어 한 벌뿐이라
        # (app/errors.py) 영어 UI 에 그대로 쓸 수 없다 — JS 가 code 로 여기서 고른다.
        "error_guess_length": "정답은 {length}글자예요.",
        "error_already_finished": "이미 끝난 퍼즐이에요.",
        "error_rate_limited": "제출이 너무 많아요. 잠시 후 다시 시도해주세요.",
        "error_no_puzzle_today": "오늘의 퍼즐이 아직 준비되지 않았어요.",
        "error_unauthorized": "기록을 확인할 수 없어요. 새로고침해주세요.",
        # 결과·공유
        "result_success": '정답은 "{answer}"였어요!',
        "result_fail": '아쉬워요, 정답은 "{answer}"였어요.',
        "share_open": "결과 공유하기",
        "share_copied": "클립보드에 복사했어요!",
        "share_heading": "오늘의 초성 {date}",
        "share_puzzle": "{mask} ({length}글자)",
        "share_success": "{used}/{max} 성공",
        "share_fail": "{used}/{max} 실패",
        "clipboard_unsupported": "클립보드 복사를 지원하지 않는 환경이에요. 직접 복사해주세요:",
        # 리더보드·통계
        "leaderboard_heading": "순위",
        "my_rank": "#{rank} · {attempts}회 · {time}",
        "my_rank_unsolved": "아직 안 풀었어요",
        "leaderboard_entry": "{display} · {attempts}회 · {time}",
        "leaderboard_empty": "아직 아무도 못 풀었어요. 첫 번째가 되어보세요",
        "leaderboard_load_failed": "순위를 불러오지 못했어요.",
        "stats_heading": "오늘의 시도 분포",
        "stats_row": "{attempt}회 {percent}%",
        "stats_empty": "아직 정답자가 없어요",
        # 섹션 토글 — 웹은 탭 대신 상단 텍스트 링크 하나로 섹션을 바꾼다(SCREENS "웹" 절).
        "section_nav_label": "화면 전환",
        "nav_today": "오늘",
        "nav_leaderboard": "순위",
        "nav_records": "내 기록",
        "records_heading": "내 기록",
        # 상태 4종 (OVERRIDES §7)
        "loading": "불러오는 중",
        "offline_banner": "오프라인이에요. 연결되면 다시 불러올게요.",
        "retry": "다시 시도",
        "network_error": "연결이 불안정해요. 다시 시도해주세요.",
        "no_puzzle_heading": "곧 새 퍼즐이 올라와요.",
        "no_puzzle_countdown": "KST 자정까지 {time}",
        # 앱 설치 CTA (US 42) — 배지 이름은 스토어가 정한 표기라 번역하지 않는다.
        "app_cta": "앱에서 연속 기록과 알림을 받아보세요",
        "store_ios": "App Store",
        "store_android": "Google Play",
        # 푸터 (US 45)
        "footer_nav_label": "약관·정책",
        "footer_privacy": "개인정보처리방침",
        "footer_terms": "이용약관",
        "footer_delete": "계정 삭제",
    },
    "en": {
        "app_title": "Hidden Vowels",
        "streak_loading": "-",
        "streak_summary": "{current}-day streak · best {max} · {solved} solved",
        "streak_load_failed": "Couldn't load your record.",
        "login_google": "Sign in with Google",
        "login_apple": "Sign in with Apple",
        "provider_google": "Google",
        "provider_apple": "Apple",
        "linked_account": "✅ Signed in with {provider}",
        "linked_account_with_email": "✅ Signed in with {provider} ({email})",
        "backup_open": "Back up my record",
        "restore_open": "Restore from another device",
        "backup_desc": "Save this code to continue the same record on another device.",
        "restore_desc": "Paste a backup code to bring that record to this device.",
        "backup_code_placeholder": "Paste backup code",
        "copy": "Copy",
        "copied": "Copied!",
        "restore_submit": "Restore",
        "restore_invalid_code": "That backup code isn't valid. Please check it again.",
        "puzzle_language_label": "Puzzle language",
        "puzzle_language_ko": "Korean",
        "puzzle_language_en": "English",
        "puzzle_language_failed": "Couldn't change the puzzle language.",
        "category_general": "General word",
        "category_book_title": "Book title",
        "length_caption": "{length} letters",
        "attempts_left": "{left}/{max} tries left",
        "hint": "Hint: {hint}",
        "guess_placeholder": "Type your answer",
        "submit": "Submit",
        "guest_issue_failed": "Couldn't start a guest session. Please try again in a moment.",
        "puzzle_load_failed": "Couldn't load today's puzzle.",
        "puzzle_changed": "There's a new puzzle",
        "account_deleted": "Your account and records were deleted. Starting fresh.",
        "generic_error": "Something went wrong.",
        "error_guess_length": "The answer is {length} letters.",
        "error_already_finished": "You've already finished this puzzle.",
        "error_rate_limited": "Too many guesses. Please try again in a moment.",
        "error_no_puzzle_today": "Today's puzzle isn't ready yet.",
        "error_unauthorized": "We couldn't check your record. Please reload.",
        "result_success": 'The answer was "{answer}"!',
        "result_fail": 'So close — the answer was "{answer}".',
        "share_open": "Share result",
        "share_copied": "Copied to clipboard!",
        "share_heading": "Hidden Vowels {date}",
        "share_puzzle": "{mask} ({length} letters)",
        "share_success": "{used}/{max} solved",
        "share_fail": "{used}/{max} failed",
        "clipboard_unsupported": "This browser can't copy for you. Please copy it yourself:",
        "leaderboard_heading": "Leaderboard",
        "my_rank": "#{rank} · {attempts} tries · {time}",
        "my_rank_unsolved": "You haven't solved it yet",
        "leaderboard_entry": "{display} · {attempts} tries · {time}",
        "leaderboard_empty": "Nobody has solved it yet. Be the first",
        "leaderboard_load_failed": "Couldn't load the leaderboard.",
        "stats_heading": "Today's attempts",
        "stats_row": "{attempt} tries {percent}%",
        "stats_empty": "No one has solved it yet",
        "section_nav_label": "Sections",
        "nav_today": "Today",
        "nav_leaderboard": "Leaderboard",
        "nav_records": "My record",
        "records_heading": "My record",
        "loading": "Loading",
        "offline_banner": "You're offline. We'll reload once you're back.",
        "retry": "Try again",
        "network_error": "The connection dropped. Please try again.",
        "no_puzzle_heading": "A new puzzle is on the way.",
        "no_puzzle_countdown": "{time} until midnight KST",
        "app_cta": "Get streaks and reminders in the app",
        "store_ios": "App Store",
        "store_android": "Google Play",
        "footer_nav_label": "Policies",
        "footer_privacy": "Privacy Policy",
        "footer_terms": "Terms of Service",
        "footer_delete": "Delete account",
    },
}


def strings_for(language: str) -> dict[str, str]:
    """그 언어의 문구 한 벌. 지원하지 않는 값이 오면 KeyError 로 바로 드러난다 —
    `resolve_ui_language` 가 늘 지원 언어만 돌려주므로 조용히 ko 로 눕히지 않는다."""
    return UI_STRINGS[language]
