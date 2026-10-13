# 티켓 03 최종 리뷰 — 라운드 1

## 검토 범위

- 기준: 로컬 `main` = `72a2a3c`, 구현 HEAD = `f3028df`; `git log main..HEAD`의 6개 커밋과 `git diff main...HEAD` 전체를 검토했다. `origin/main`은 사용하지 않았다.
- 티켓 03, 스펙 §A.1–4·§A′·Testing, `CONTEXT.md`, 구현 증거를 읽고 코드 및 실제 실행 결과와 대조했다. 후속 범위는 티켓 04·05 원문으로 확인했다.
- UI 변경이 없어 디자인 검토는 해당 없음. 애플리케이션·테스트·설정·`.scratch/`는 수정하지 않았다.

## 체크박스별 충족 여부

| 티켓 항목 | 판정 | 직접 확인한 근거 |
|---|---|---|
| 생성 시 언어 선택·ko 기본·미지원 값 오류, PATCH 변경, 내 통계 언어 | 충족 | `app/api/guests.py:11`, `app/api/me.py:11`, `app/schemas/guest.py`, `app/services/stats_service.py`. `tests/test_guest_language.py`가 DB 저장·변경 유지·400·401·응답 필드를 검증한다. |
| 선호 언어 퍼즐과 puzzle_id/language/mask/length, chosung 호환 | 충족 | `app/services/puzzle_service.py:45` 및 `:59`, `app/schemas/puzzle.py`. ko 초성 유지, en `_PPL_`, 공백 제외 length, 미배정 언어 404를 `tests/test_puzzle_language_api.py`에서 검증한다. |
| 퍼즐·통계·리더보드 언어별 키, rate limit 언어 무관 | 충족 | `app/services/puzzle_cache.py:37`, `app/services/puzzle_metrics.py:16`, 기존 rate limit 경로 유지. API 테스트가 실제 Redis 키별 값을 읽고 `test_rate_limit_counter_survives_a_language_change`가 언어 변경 후 11번째 요청의 429를 검증한다. |
| 통계·리더보드 명시 언어/기본 선호, 응답 language | 충족 | `app/api/puzzles.py:15`, `:47`, `:56`에서 같은 언어를 퍼즐 조회와 집계에 전달한다. 언어별 정답자·리더보드 분리 및 잘못된 쿼리 값 400 테스트가 있다. |
| 날짜 기준 streak 및 같은 날 두 정답 solved_count +2 | 충족 | `app/services/guess_service.py:108`의 당일 no-op은 streak에만 적용되고 solved_count는 매번 증가한다. GuestStats 잠금 경로가 유지되며 `tests/test_streak.py`에서 어제 streak 3 → ko/en 정답 후 4, solved_count 2를 검증한다. |
| ko/en 공존·변경 후 조회/캐시 분리·기존 회귀·언어 팩토리 | 충족 | `tests/conftest.py:46`의 `make_today_puzzle(language)`와 기존 ko `today_puzzle` 래퍼가 기능을 제공한다. 명칭은 티켓의 `today_puzzle(language)`와 다르지만 실제 언어별 생성 및 기존 사용처 호환을 확인했다. 전체 208개 테스트가 통과했다. |
| README 설계 판단 2항목 및 API 표 | 충족 | `README.md:506`부터 03 소제목 3개와 API 필드·PATCH·쿼리 설명이 있다. 단, 공통 추가 전용 규칙 위반은 별도 D-03-1이다. |

## 독립 실행 검증

- 로컬 기존 `chosung_daily_test_t03`, `chosung_daily_test_t03_migrations` 및 Redis `127.0.0.1:6379/5`를 사용했다. `TEST_DATABASE_URL`, `TEST_MIGRATION_DATABASE_URL`, `TEST_REDIS_URL`로 지정했고 새 DB 생성이나 기본 DB 폴백은 하지 않았다. 접속 비밀 값은 기록하지 않는다.
- 위 환경에서 `uv run pytest -q`: exit 0, **208 passed in 100.06s**. 실패·skip·xfail 없고 간헐 실패 재실행도 필요 없었다.
- `uv run ruff check .`: exit 0, `All checks passed!`.
- `uv run flask --app wsgi db heads`: exit 0, `4e72a4045fbc (head)` 한 줄. 이 티켓 자체의 마이그레이션 추가는 없다.
- `git diff --check main...HEAD`: exit 0.
- 신규 언어 API 테스트는 서비스 전체를 mock하지 않고 실제 Flask 요청·MySQL 상태·Redis 키를 검증한다. 캐시 hit/장애 및 동시 제출 기존 테스트도 검토했으며 항상 통과하도록 변경한 흔적은 발견하지 못했다.

## 결함 목록

### D-03-1 — README 공통 영역을 덧붙이기 대신 직접 수정함

- 심각도: **MINOR**
- 위치: `README.md:81`, `README.md:213`, `README.md:224`, `README.md:229`.
- 근거: 티켓 공통 규칙은 README 설계 판단·API 표를 자기 번호 소제목/자기 행으로 **섹션 끝에 덧붙이기**로 제한한다.
- 재현: `git diff main...f3028df -- README.md`를 확인한다.
- 기대: 기존 공통 설계 판단 본문과 API 행은 보존하고, 03 전용 소제목/행을 섹션 끝에 추가한다.
- 실제: 기존 API 행 5개를 교체하고 PATCH 행을 표 중간에 넣었으며, 기존 번호 없는 Redis 설계 판단 문단 3곳도 수정했다. 뒤에 올바르게 추가한 03 소제목과 별개로 규칙 위반이다.
- 영향: 병렬 티켓 04·05·07 등이 갱신하는 공유 문서에서 충돌/덮어쓰기 가능성이 커진다. 현재 기능 동작이나 데이터 손상을 입증한 문제는 아니므로 MINOR로 분류한다. 기존 문단 수정분을 03 전용 추가 절/행으로 옮기면 된다.

## 보안·범위 및 참고

- PATCH는 Bearer `with_guest`로 보호되고 쿠키 세션 인증을 사용하지 않는다. 언어 값은 enum 검증을 거치며, 퍼즐 응답은 종료 전 정답을 내보내지 않는다. 변경분에서 실제 키·토큰·비밀번호의 파일 기록이나 새 인증 우회는 발견하지 못했다.
- 제출의 puzzle_id 고정·영어 대소문자/구분자 정규화·attempts 복원은 티켓 04, 언어별 배정·통계 flush는 티켓 05가 명시적으로 소유하므로 03 결함에 포함하지 않았다. 출시 전체 완료를 의미하는 판정은 아니다.
- `make_today_puzzle` 명칭 변경은 기존 픽스처 호환성을 유지하면서 요구 기능을 제공한다. 증거 문서의 승인 주장은 별도로 검증하지 않았으며, 승인 주장 대신 실제 기능을 기준으로 충족 판정했다.
- 취향·스타일 제안은 결함으로 올리지 않았다.

BLOCKER 0건 / MAJOR 0건 / MINOR 1건. 규칙 축에서 D-03-1, 기능·스펙 축에서 추가 결함 없음.

판정: PASS
