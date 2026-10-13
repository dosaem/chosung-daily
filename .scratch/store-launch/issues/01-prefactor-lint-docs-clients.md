# 01: 프리팩터 — 린트 강화·도메인 문서 루트 이관·외부 호출 골격

**What to build:** 이후 모든 백엔드 티켓이 같은 틀 위에서 시작하도록 바닥을 다진다. 사용자 입장에서 보이는 변화는 없지만, CI 가 ruff 엄격 규칙으로 통과하고, 용어집·ADR 이 레포 루트에서 읽히며, 외부 서비스 호출(Slack 등)이 `clients/` 한 곳에 "함수 하나 = 래퍼 하나" 로 모이기 시작한다. 운영자가 Slack 으로 첫 테스트 알림을 받을 수 있다.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.12, §A.17, §C.31, §C.32, Further Notes. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] `.scratch/store-launch/CONTEXT.md` 를 레포 루트 `CONTEXT.md` 로, `.scratch/store-launch/adr/0001~0003` 을 `docs/adr/` 로 옮기고(원본은 `.scratch` 에 그대로 둬도 됨) `docs/agents/domain.md` 가 가리키는 경로와 일치한다
- [ ] `/impeccable init` 을 실행해 생성된 설정이 커밋되고, DESIGN_DIR(`.scratch/store-launch/design/`, `design-system/hidden-vowels/`) 을 가리킨다
- [ ] ruff 설정에 `PL,RUF,SIM,PT` 규칙이 추가되고 기존 코드가 수정돼 CI 린트 잡이 통과한다(규칙 완화·`noqa` 남발 금지, 예외는 pyproject 에 근거 주석)
- [ ] `app/clients/` 패키지가 생기고 첫 클라이언트로 Slack Incoming Webhook 래퍼(함수 하나, 타임아웃 3초, 실패해도 예외를 호출자에게 던지지 않고 로그)가 들어간다. `SLACK_WEBHOOK_URL` 이 비어 있으면 no-op
- [ ] 운영자 알림 서비스 함수 `notify_operator(kind, message)` 가 있고, 테스트는 monkeypatch 한 래퍼로 호출 인자(제목·본문)를 검증한다. 네트워크 호출 없음
- [ ] README "설계 판단" 절에 "외부 호출 래퍼와 도메인 판정 함수의 분리", "Slack Webhook 선택 근거" 항목이 추가된다
- [ ] `.env.example` 에 `SLACK_WEBHOOK_URL` 이 추가된다. `.env*` 실제 값은 건드리지 않는다
