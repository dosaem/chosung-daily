# 티켓 02 최종 리뷰 — 라운드 1

- 검토일: 2026-10-14
- 기준: 로컬 `main` = `491418fb4b7b3ebae9a0205443381456ef4821f9`, 구현 HEAD = `d3752b9c463291838cbc0621b784c3c3ca6a5f12`.
- `git diff main...HEAD` 전체 20파일과 `git log main..HEAD`의 구현 커밋 `c9e8007`, `517ef79`, `d3752b9`를 확인했다. `origin/main`은 사용하지 않았다.
- 기준 문서: `.scratch/store-launch/issues/02-puzzle-language-migration-mask.md`, 스펙 §A.1의 스키마·모델 분할 범위, §A.2 가림 포맷, Testing Decisions, `CONTEXT.md`, `review/impl-evidence-02.md`.
- UI 변경이 없어 디자인 검토는 해당 없음. 애플리케이션·테스트·설정·`.scratch/`는 수정하지 않았다.

## 체크박스별 판정

| 티켓 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| 마이그레이션 1개, Word.language/mask, DailyPuzzle 날짜·언어 유니크, Guest 기본 ko, chosung 유지, DailyStats 언어 키 | 충족 | `migrations/versions/4e72a4045fbc_add_puzzle_language_and_mask.py:41`의 upgrade와 모델 정의를 대조했다. 실제 DB를 사용하는 `test_puzzle_language_model.py` 11개 및 마이그레이션 테스트 4개 통과. 동일 날짜 ko/en 공존, 동일 날짜·언어 중복 거부, 기본 ko, 통계 복합키를 검증한다. |
| 별도 DB + flask db 서브프로세스로 upgrade → 삽입 → downgrade → upgrade 및 ko 데이터 보존 | 충족 | `tests/test_migrations.py:48`의 subprocess 호출 및 독립 `migration_engine` 픽스처 확인. `test_korean_data_survives_downgrade_and_upgrade`는 실제 SQL로 단어·퍼즐·시도·게스트·통계 스냅샷을 비교한다. conftest의 create_all 경로를 사용하지 않으며 4개 모두 실제 실행에서 통과했다. |
| 순수 가림 함수와 s 제외 length, apple/공백/하이픈/대문자 테스트 | 충족 | `app/utils/mask.py:31`의 build_mask와 `:38`의 mask_length는 DB·외부 호출 없이 계산한다. `tests/test_mask.py` 17개 통과: apple은 `_PPL_`, harry potter는 공백 s 및 길이 11, spider-man은 하이픈 s 및 길이 9, 대소문자 동일 결과. ko는 기존 초성 계산 함수를 공유한다. |
| 저장 시 mask 계산 및 기존 ko 단어 backfill | 충족 | `app/models/word.py:36`의 insert/update 이벤트가 언어 기본값과 mask·chosung을 계산한다. CSV/책 등록 서비스의 실제 저장 테스트 및 answer/language 변경 테스트 통과. 마이그레이션 `:104`의 backfill은 이전 스키마에서 삽입한 단어로도 검증된다. |
| 기존 테스트 전부 ko 기본값으로 통과 | 충족 | 전체 `146 passed`. 기존 `test_puzzle_maintenance.py` 변경은 복합 PK 조회와 명시적 ko 삽입으로, 기존 결과 단언을 제거하거나 약화하지 않았다. 유지보수 서비스도 ko 복합키에 기록하도록 함께 변경됐다. |
| flask db heads 1개 | 충족 | 직접 실행한 출력은 `4e72a4045fbc (head)` 한 줄. 이후 다른 티켓 병합 시 코디네이터의 재확인은 필요하다. |
| README 설계 판단에 퍼즐 언어 모델·가림 포맷 추가 | 충족 | `README.md:387`부터 설계 판단 절 끝에 `### 02.` 항목 2개가 추가됐다. 단일 마이그레이션 선택 근거와 타일 형식·저장 시 계산을 설명한다. |

## 직접 실행한 검증

구현 증거의 실행 결과를 인용해 판정하지 않고 다음을 새로 실행했다.
접속 URL의 인증 부분은 문서에 기록하지 않는다. 로컬 MySQL의 기존 `chosung_daily_test_t02`를 `TEST_DATABASE_URL`로, Redis DB 4를 `TEST_REDIS_URL`로, 기존 `chosung_daily_test_t02_migrations`를 `TEST_MIGRATION_DATABASE_URL`로 지정했다. 새 DB 생성 및 기본 DB로의 폴백은 없었다.

| 명령 | 실제 결과 |
|---|---|
| 위 세 환경변수 지정 후 `uv run pytest -q` | 종료 0, `146 passed in 83.23s (0:01:23)`; 실패·skip 없음 |
| `uv run ruff check .` | 종료 0, `All checks passed!` |
| `FLASK_APP=wsgi.py uv run flask db heads` | 종료 0, `4e72a4045fbc (head)` 한 줄 |
| `git diff --check main...HEAD` | 종료 0, 출력 없음 |

간헐 실패가 없어 재실행은 하지 않았다. ruff 설정은 기존대로 migrations를 제외하므로 마이그레이션 자체는 코드 검토와 실제 upgrade/downgrade 실행으로 확인했다.

## 결함 목록

없음. BLOCKER 0 / MAJOR 0 / MINOR 0.

## 범위·보안·공유 파일 확인

- 신규 테스트는 가림 출력, 실제 MySQL 행과 유니크 제약, 실제 Alembic subprocess 동작을 검증한다. 신규 테스트에 동작을 대신하는 mock이나 무조건 통과하는 단언은 없다. backfill 테스트의 기대값은 같은 순수 함수를 사용하지만 그 함수의 타일 결과는 별도 단위 테스트에서 구체적인 값으로 검증한다.
- 이번 diff는 인증·CSRF·공개 API 경계를 변경하지 않는다. CSV의 알려지지 않은 언어는 건너뛰고, DB 언어 컬럼은 ko/en enum이다. 숨긴 모음의 c에는 정답 대신 빈 문자열을 저장한다.
- 변경분에 실제 서비스 키·토큰·비밀번호 노출은 발견하지 못했다. CI 및 README의 DB 예시는 로컬 테스트 컨테이너용 설정이며 `.env.example` 신규 설정값은 비어 있다. 이 리뷰에는 인증값을 기록하지 않았다.
- 공유 README 설계 판단은 자기 번호 항목만 절 끝에 추가했으며 API 표는 변경하지 않았다. `.env.example`은 자기 번호 주석과 신규 설정 행을 끝에 추가했다. README 실행 안내와 CI의 테스트 DB 준비는 신규 왕복 테스트를 실행하기 위한 변경이다.
- 스펙에 따라 서비스/API·캐시·자정 배정 언어 인지화는 후속 티켓 범위다. 이번 변경에서 이를 구현하지 않은 것은 누락 결함으로 분류하지 않았다.

## 참고 및 검증 한계

- `migrations/versions/4e72a4045fbc_add_puzzle_language_and_mask.py:68`의 downgrade는 영어 시도·퍼즐·단어·통계를 삭제한다. ko 보존 요구는 실제 왕복 테스트에서 충족하지만, 이 PASS는 영어 데이터까지 보존하는 롤백을 의미하지 않는다. 영어 데이터 보존은 이 티켓의 명시적 왕복 승인 조건에 포함되지 않는다.
- 현재 배정 서비스는 언어 필터가 없으므로 영어 단어를 넣으면 ko 퍼즐에 영어 단어를 배정할 수 있다. 코드와 구현 증거에서 이를 확인했으며, 후속 자정 배정·캐시 티켓 통합 전 영어 운영 투입의 제한사항으로 남긴다.
- 구현 증거 첫머리의 변경 파일 수 19개와 실제 diff의 20개는 다르다. 요구 동작 판정에는 영향이 없는 문서 집계 차이다.
- 로컬 테스트만 실행했다. 프로덕션/NAS 접속, 배포, 외부 서비스 직접 호출, push는 하지 않았다. CI 원격 실행은 검증하지 않았다.

판정: PASS
