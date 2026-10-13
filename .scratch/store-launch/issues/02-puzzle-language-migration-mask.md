# 02: 퍼즐 언어 마이그레이션·모델·가림 포맷

**What to build:** 단어와 오늘의 퍼즐이 언어(ko/en)를 가지며, 같은 날짜에 ko 와 en 퍼즐이 각각 하나씩 공존할 수 있다. 단어를 저장하면 언어에 맞는 가림(`mask`)이 계산돼 함께 저장된다 — ko 는 초성, en 은 모음 빈칸. 게스트는 퍼즐 언어 선호(기본 ko)를 갖는다. 기존 데이터는 마이그레이션 후 전부 ko 로 남아 있고 기존 테스트가 그대로 통과한다. 이 티켓은 스키마·모델·순수 함수까지이며 API 는 다음 티켓.

**Blocked by:** 01

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.1(마이그레이션+모델), §A.2 가림 포맷, Testing 회귀. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] Alembic 마이그레이션 1개: `Word.language`(기본 ko), `DailyPuzzle (puzzle_date, language)` 유니크, `Guest.puzzle_language`(기본 ko), `Word.mask`(JSON) — 기존 `chosung` 컬럼은 남긴다(응답 호환용, 미정 10). `DailyStats` 키에 언어 포함
- [ ] 마이그레이션 왕복 테스트 `tests/test_migrations.py`: 별도 DB 이름을 만들고 `flask db upgrade` → 데이터 삽입 → `downgrade` → `upgrade` 를 서브프로세스로 돌려 ko 단어·퍼즐·시도가 동일하게 조회됨(conftest 의 `create_all` 경로와 분리)
- [ ] 가림 계산은 순수 함수: 입력(언어, 정답) → `[{t: r|h|s, c}]`. ko 는 초성 추출(현행 로직 이동), en 은 a/e/i/o/u 를 `h`, 공백·하이픈을 `s`, 나머지 `r`. `length` 는 `s` 제외 글자 수. 단위 테스트: `apple`→`_PPL_`, `harry potter`(공백 `s`), 하이픈, 대문자 입력
- [ ] 단어 저장 서비스 함수(현행 `add_word` 류)가 저장 시 `mask` 를 계산해 넣고, 기존 ko 단어는 마이그레이션 데이터 단계에서 `mask` 가 채워진다
- [ ] 기존 테스트 전부 ko 기본값으로 통과(리더보드 응답 필드 교체는 07 에서)
- [ ] 머지 직전 `flask db heads` 1개
- [ ] README "설계 판단" 에 "퍼즐 언어 모델 — expand-contract 대신 마이그레이션 1개(트래픽 운영자뿐)", "가림 포맷" 항목 추가

## 리뷰 노트 (plan-review r1)

- P1-19: 왕복 테스트 방식을 `tests/test_migrations.py`(별도 DB + `flask db` 서브프로세스)로 확정
- P1-21: 리더보드 필드 교체 담당을 07 로 바로잡음
