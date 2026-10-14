# 티켓 23 최종 리뷰 — 라운드 1

- 기준: 로컬 `main` = `7df78098f9c25baea9c47eb4cabf1c853ed9799f`, 구현 HEAD = `9381c2c90a928dbbf34e74b6ce49f857900ba3cb`.
- `git diff main...HEAD`, `git log main..HEAD`의 구현·증거 3커밋, 티켓, spec §A.11·A.14·US 54/55/58/59, CONTEXT, README 설계 판단, 디자인 SCREENS·OVERRIDES를 직접 검토했다. 하위 에이전트 없이 수행했다.
- 결함: BLOCKER 0 / MAJOR 1 / MINOR 0. 코드·테스트·설정·`.scratch/` 수정 없음.

## 티켓 체크박스별 판정

| 체크박스 | 충족 여부 | 직접 확인한 근거 |
|---|---|---|
| 언어 탭·오늘부터 30일·단어/미배정 표시·교체·캐시 무효화·시도 있는 날짜 교체 금지 | **미충족** | `app/admin.py:229`, `web/templates/admin/schedule.html`, `upcoming_schedule`로 ko/en 30일과 미배정 문구 표시. 교체 및 실제 캐시 선충전 후 무효화 테스트 통과. 그러나 D-23-1로 동시 제출 시 시도가 있는 퍼즐이 교체되어 이력이 손상된다. 명시된 `schedule_puzzles(language, days)` 자체를 호출하지 않고 같은 모듈의 조회 함수·30일 상수만 재사용한다. 읽기에서 배정을 만들지 않는 이유는 README `### 23.`에 설명되어 있다. |
| 05 잔량 서비스 재사용·14일 미만 경고 색 | **충족** | `remaining_days_by_language()`와 `LOW_WORD_POOL_THRESHOLD_DAYS` 재사용, `admin-stock-low` 조건과 destructive 테두리·문구 확인. 실제 배정 전후 잔량 및 14일 경계 테스트 통과. |
| 점검 모드/메시지·iOS/Android 최소 버전 → AppSetting 저장 → `/config` 즉시 반영 | **충족** | 설정 4키의 단일 커밋, 저장 전 입력 검증, `app_config` 캐시 삭제 확인. 실제 HTTP로 캐시를 먼저 채우고 설정 저장 직후 새 응답을 검증하는 테스트 통과. CSRF 누락 거부도 통과. |
| Google Books 단일 래퍼·카카오와 같은 서비스 시그니처·선택해서 en 단어 추가·자동 가림·선택 API 키 | **충족** | `search_volumes(query, size=5)`와 `search_google_books(query, size=5)`의 요청/매핑 확인. provider HTTP 경계만 대체한 테스트에서 en/book_title DB 행·모음 가림·중복·길이 제한·CSRF를 확인했다. `.env.example` 키 기본값은 비어 있다. 실제 Google 왕복은 금지 조건 때문에 수행하지 않았다. |
| impeccable detect 0건·README 운영 절 | **증거 부족** | README 운영 절은 충족. 직접 생성한 실제 렌더 HTML로 detect를 실행했지만 외부 CDN 차단을 위해 스냅샷의 폰트 링크를 제거한 조건이라 원래 폰트 환경의 0건을 확인하지 못했다. 데스크톱 책 검색 3상태에서 line-length 3건, 모바일 4화면은 0건. 세부 결과와 한계는 아래 기록. |

## 직접 실행한 검증

테스트는 기존 전용 DB `chosung_daily_test_t23`와 Redis DB 11에 각각 `TEST_DATABASE_URL`, `TEST_REDIS_URL`을 지정했다. 로컬 접속은 `.env.example` 형식과 TestingConfig 기본 접속값을 사용했으며 접속 문자열은 문서에 기록하지 않는다. 새 DB 생성 및 기본 테스트 DB로의 폴백은 없었다. 테스트 픽스처의 테이블 생성/정리만 수행했다.

```text
uv run pytest tests/test_admin_schedule.py tests/test_admin_settings.py \
  tests/test_admin_books.py tests/test_google_books.py \
  tests/test_puzzle_schedule_service.py tests/test_app_config.py \
  tests/test_word_service.py tests/test_admin_css.py -q
113 passed in 141.70s (0:02:21), exit 0

uv run pytest tests/test_admin_auth.py tests/test_csrf.py -q
17 passed in 17.34s, exit 0

uv run ruff check .
All checks passed!, exit 0

FLASK_ENV=testing uv run flask --app wsgi db heads
94a83f12fddb (head)
exit 0, 정확히 1줄

git diff --check main...HEAD
출력 없음, exit 0
```

마이그레이션 변경은 없다. 전체 870개 테스트를 재실행했다는 주장은 하지 않는다. 이 리뷰에서는 영향 범위와 보안 회귀 130개를 직접 실행했다. 실패·간헐 오류가 없어 재실행은 불필요했다.

UI 검증은 기존 `review/admin-detect-snapshot-23.py`를 같은 테스트 자원으로 실행해 `/tmp/t23-final-review-snapshots`에 10개 실제 응답 HTML과 CSS를 만들었다. Google 응답은 기존 스크립트의 provider 대역을 사용했다. 외부 서비스 호출 금지를 지키기 위해 임시 HTML의 CDN 폰트 `<link>`만 제거했다(레포 템플릿/CSS는 변경하지 않음). 캐시된 CLI를 `npm exec --offline -- impeccable detect --json`으로 사용하여 `file:///tmp/t23-final-review-snapshots/<name>.html`을 브라우저 모드로 검사했다.

| 조건 | 결과 |
|---|---|
| 기본 1280×800, schedule_low/ok/en/replace/replace_empty, settings/settings_error, books/books_form/books_empty | books/books_form/books_empty 각각 `line-length: ~88 chars/line (aim for <80)`; 합계 3건, exit 2 |
| `--viewport 390x844`, schedule_low/replace, settings, books | `[]`, exit 0 |

이 결과는 증거 문서의 원래 CDN 폰트 조건을 동일하게 재현한 결과가 아니다. 폴백 조건의 탐지 결과를 별도 기능 결함 또는 취향 지적으로 집계하지 않았으며, 원래 조건의 0건 주장도 그대로 승인하지 않았다.

## 결함 목록

### D-23-1 — 시도 없음 검사와 교체가 원자적이지 않아 제출 이력이 다른 정답으로 바뀜

- 심각도: **MAJOR**
- 위치: `app/services/puzzle_schedule_service.py:206` (조회·시도 수 검사·word_id 변경·커밋, 특히 208~221행).
- 요구: 티켓 첫 체크박스의 “이미 시도가 있는 날짜(오늘·과거)는 교체 금지”.
- 원인: `count_by_puzzle`의 일반 SELECT가 0을 읽은 뒤 `word_id`를 UPDATE할 때까지 다른 세션의 첫 제출을 막지 않는다. 제출 경로는 GuestStats만 잠그고 이 교체와 공유하는 잠금/재검증이 없다. 따라서 제출이 먼저 커밋되어도 교체가 성공한다. 캐시 삭제는 이미 생긴 Attempt·정답 판정·통계 불일치를 복구하지 못한다.
- 실제 재현: 전용 MySQL/Redis에서 오늘 ko 퍼즐(사과), 대체 단어(학교), 게스트를 만들었다. 원래 `count_by_puzzle`을 실제로 실행한 직후 별도 Flask app context/DB 세션으로 실제 `submit_guess(..., '사과')`를 실행·커밋하고, 원래 조회 결과를 반환하여 교체를 계속했다. 조회값이나 제출 결과를 가짜로 만들지 않고 실행 순서만 고정했다.

재현 핵심 코드(같은 테스트 환경에서 `db.create_all()` 후 준비한 `app`, 오늘 `today`, 기존 `pid`, 대체 `wid`, 게스트 `gid` 사용):

```python
from unittest.mock import patch
from app.extensions import db
from app.models import Guest, PuzzleLanguage
from app.repositories import attempt_repository
from app.services.guess_service import submit_guess
from app.services.puzzle_schedule_service import replace_assignment
from app.services.puzzle_service import get_today_puzzle_view

original = attempt_repository.count_by_puzzle

def interleave(ids):
    counts = original(ids)  # 실제 MySQL 조회: 시도 0건
    print('replacement attempt count:', counts)
    with app.app_context():  # 별도 세션에서 실제 제출과 커밋
        result = submit_guess(db.session.get(Guest, gid), pid, '사과')
        print('concurrent submission is_correct:', result.is_correct)
    return counts

with patch.object(attempt_repository, 'count_by_puzzle', side_effect=interleave):
    replace_assignment(today, PuzzleLanguage.KO, wid)
db.session.remove()
view = get_today_puzzle_view(db.session.get(Guest, gid))
print(view.status, view.answer, [a.model_dump() for a in view.attempts])
```

```text
replacement attempt count: {}
concurrent submission is_correct: True
saved attempt: [('사과', True)]
restored view: success 학교 [{'guess': '사과', 'feedback': [False, False]}]
```

- 기대: 사과 정답 제출이 커밋된 경우 교체를 거부하여 사과·성공 이력을 유지하거나, 교체가 먼저 완료되는 순서에서는 제출을 새 퍼즐 기준으로 안전하게 재검증해야 한다.
- 실제: 제출과 교체가 모두 성공하며 “성공, 정답 학교, 사과 제출의 모든 글자는 틀림”이라는 모순된 보드가 복원된다. 이미 기록한 solved_count·리더보드도 옛 정답의 성공으로 남는다.
- 기존 테스트 한계: `test_replacing_a_day_that_has_attempts_is_refused`, `test_replace_assignment_is_blocked_once_the_day_has_attempts`는 교체 시작 전 시도가 존재하는 순차 상황만 검사한다. 캐시 무효화 테스트도 동시 제출은 다루지 않는다.
- 수정 시 확인할 범위: 교체와 제출이 공유하는 트랜잭션 보호 및 잠금 이후 최신 정답 재검증을 함께 검증해야 한다. 교체 함수에만 잠금을 붙이고 제출의 캐시/정답 스냅샷을 그대로 두면 반대 순서의 경합이 남을 수 있다.

## 표준·보안·범위 확인 및 참고

- 새 GET/POST 라우트 모두 `admin_required`, 모든 새 POST는 `csrf_protected` 적용. 템플릿 자동 escape를 우회하지 않는다. Google 예외는 타입명만 노출해 요청 URL의 선택 키를 화면에 내보내지 않는다.
- 설정 형식/길이, 책 제목·힌트 길이, 교체 단어의 존재/언어 및 날짜 범위를 확인했다. DB·캐시 테스트를 과한 mock으로 우회한 정황은 없다. Google 테스트의 HTTP 대역은 외부 호출 금지 조건에 맞는다.
- 공유 파일 diff는 README API 자기 행과 설계 판단 `### 23.`, `.env.example` `[23]`, RELEASE `### 23.`, 스펙 미정 항목의 티켓 23 행 추가다. 기존 다른 티켓 블록 수정은 없고 README 운영 절은 요청된 범위다.
- 변경 파일에서 실제 키·토큰·비밀번호가 새로 기록된 정황은 발견하지 못했다. 테스트의 명시적 더미 값과 설정 키 이름은 실제 시크릿으로 집계하지 않았다.
- 운영자 1040px 폭은 기존 README 티켓 15의 결정에 근거한다. 점검 활성화 시 메시지 필수·중복 배정 허용·조회 시 자동 배정을 하지 않는 결정은 README/증거에 설명되어 있으며 이 리뷰에서 취향 결함으로 올리지 않았다.
- 프로덕션/NAS/배포/실제 외부 API에 접근하지 않았고 push하지 않았다.

판정: FAIL
