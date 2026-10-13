# 01: 프리팩터 — 린트 강화·도메인 문서 루트 이관·외부 호출 골격·CSRF 헬퍼·마이그레이션 head 검사

**What to build:** 이후 모든 백엔드 티켓이 같은 틀 위에서 시작하도록 바닥을 다진다. 사용자 입장에서 보이는 변화는 없지만, CI 가 ruff 엄격 규칙으로 통과하고 Alembic head 가 하나임을 검사하며, 용어집·ADR 이 레포 루트에서 읽히고, 외부 서비스 호출(Slack 등)이 `clients/` 한 곳에 "함수 하나 = 래퍼 하나" 로 모이기 시작한다. 웹 폼용 CSRF 헬퍼가 준비돼 14·15·16 이 재사용한다. 운영자가 Slack 으로 첫 테스트 알림을 받을 수 있다.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.7(CSRF), §A.11, §A.12, §A.17, §C.31, §C.32, Further Notes. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] `.scratch/store-launch/CONTEXT.md` 를 레포 루트 `CONTEXT.md` 로, `.scratch/store-launch/adr/0001~0003` 을 `docs/adr/` 로 복사하고(`.scratch` 원본은 그대로 둔다; 이후 갱신은 `docs/adr/` 사본에) `docs/agents/domain.md` 가 가리키는 경로와 일치한다
- [ ] `/impeccable init` 을 실행해 생성된 설정이 커밋되고, DESIGN_DIR 두 경로(`.scratch/store-launch/design/`, `.scratch/store-launch/design-system/hidden-vowels/`)를 가리킨다(Claude 워커 전용 도구 — 코디네이터는 이 티켓을 Claude 워커에 배정)
- [ ] ruff 설정에 `PL,RUF,SIM,PT` 규칙이 추가되고 기존 코드가 수정돼 CI 린트 잡이 통과한다(규칙 완화·`noqa` 남발 금지, 예외는 pyproject 에 근거 주석)
- [ ] CI 에 "`flask db heads` 출력이 정확히 1줄" 검사 스텝이 추가된다(병렬 마이그레이션 티켓의 다중 head 를 머지 전에 잡는다)
- [ ] `app/clients/` 패키지가 생기고 첫 클라이언트로 Slack Incoming Webhook 래퍼(함수 하나, 타임아웃 3초, 실패해도 예외를 호출자에게 던지지 않고 로그)가 들어간다. `SLACK_WEBHOOK_URL` 이 비어 있으면 no-op
- [ ] 운영자 알림 서비스 함수 `notify_operator(kind, message)` 가 있고, 테스트는 monkeypatch 한 래퍼로 호출 인자(제목·본문)를 검증한다. 네트워크 호출 없음
- [ ] 웹 폼 CSRF 헬퍼: 세션에 1회용 토큰을 심는 함수 + 폼 hidden 값을 검증하는 데코레이터(불일치 403 `FORBIDDEN`). 아직 쓰는 라우트는 없고 단위 테스트만(토큰 발급·검증·재사용 거부)
- [ ] README "설계 판단" 절을 `### NN.` 소제목 구조로 시작하고 "외부 호출 래퍼와 도메인 판정 함수의 분리", "Slack Webhook 선택 근거", "CSRF 토큰 방식" 항목을 추가한다
- [ ] `.env.example` 에 `SLACK_WEBHOOK_URL` 이 추가된다. `.env`·`.env.prod.example` 실제 값은 건드리지 않는다

## 리뷰 노트 (plan-review r1)

- P1-20: `/impeccable` 은 Claude 플러그인 스킬 — 01·09·15·16·18(detect), 22~31(`audit.native`) 은 Claude 워커 배정 (코디네이터 메모)
- P1-13: 병렬 티켓의 공유 파일(README 설계 판단·API 표·`.env.example`·RELEASE.md·스펙 미정 항목) 충돌 규칙은 이 티켓이 README 구조(`### NN.`)로 시작하고 전 티켓 공통 규칙 줄로 반영함
- P2-18: CSRF 헬퍼를 14 에서 이 티켓으로 옮김 — 15 가 14(06·10·12 체인) 를 기다리지 않게 됨
- P1-02(b): 다중 head 방지는 CI `flask db heads` 검사 + 각 마이그레이션 티켓 완료 조건 + 번호순 머지로 처리(체인으로 묶지 않아 병렬 유지)
