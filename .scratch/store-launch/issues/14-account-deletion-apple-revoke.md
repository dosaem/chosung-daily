# 14: 계정 삭제 — API·웹 페이지·애플 연결 철회·재시도

**What to build:** 플레이어가 앱(`DELETE /me`) 또는 웹 `/account/delete` 에서 계정과 모든 기록을 지울 수 있다. 웹은 로그인된 세션 + 확인 폼 + CSRF 토큰(01 헬퍼)을 거치고 GET 으로는 절대 삭제되지 않는다. 애플 계정이면 애플 쪽 연결(Sign in with Apple)도 실제로 철회되며, 철회 실패는 매일 재시도하고 7일 뒤 폐기한다. 삭제 후 옛 토큰은 401 이고 웹은 새 게스트로 시작한다.

**Blocked by:** 06, 09, 10, 11, 12

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.7, US 21·22·22a, 미정 11. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] 삭제 서비스 함수 하나가 Attempt, GuestStats, Account, HintUnlock, Subscription, 오늘 리더보드 `ZREM`(언어별), Guest 삭제를 한 트랜잭션으로 수행하고 커밋한다. 삭제 후 Bearer 요청 401
- [ ] `GET /account/delete`: 로그인 세션이면 확인 폼(ko/en, "되돌릴 수 없음·구독은 스토어에서 따로 해지", 09 의 토큰 CSS), 아니면 안내 + 운영자 메일. `POST /account/delete`: 세션 없음 401, 01 의 CSRF 검증 불일치 403, 성공 시 세션 비우고 `/` 리다이렉트. GET 은 상태 변경 없음(테스트)
- [ ] 애플 revoke: `clients/apple.py` 에 revoke 래퍼 추가, 저장된 `refresh_token` 과 `provider_client_id` 에 맞는 client_id·client_secret(iOS 연결 = 번들 ID, 웹 연결 = Services ID; 11 의 공개 접근자 사용)으로 호출. 테스트: 두 경우 각각 올바른 client_id 로 호출됨
- [ ] revoke 실패 시 삭제는 진행하고 `AppleRevocationRetry(refresh_token_enc, client_id, created_at)` 행 생성(마이그레이션, 머지 직전 `flask db heads` 1개), Beat 매일 재시도, 7일 초과 폐기 + `notify_operator`
- [ ] 웹 프론트: 삭제 성공 리다이렉트 후 localStorage 토큰을 버리고 새 게스트를 발급한다(JS 최소 변경 + 수동 체크리스트 항목)
- [ ] `/account/delete` 확인 페이지에 삭제되는 데이터 목록(개인정보처리방침 "수집하는 정보" 절과 같은 이름)과 방침의 파기·권리 행사 절 링크를 넣는다. 문구의 법 기준 점검·보완은 16 이 하므로 문구는 템플릿(ko/en 각 1개)에 두고 테스트는 핵심 단어("되돌릴 수 없", 스토어 해지)만 고정한다
- [ ] `impeccable detect` 0건(`/account/delete`), README "설계 판단" 에 "삭제 한 커밋·애플 revoke 재시도" 추가, Play Data safety 삭제 URL 로 `/account/delete` 명시
- [ ] 분할선(세션이 모자라면): "revoke 재시도 테이블·Beat·7일 폐기" 를 뒤로 떼어 별도 티켓으로 — 그 경우 코디네이터에게 알리고 삭제 자체는 revoke 1회 시도까지로 닫는다

## 리뷰 노트 (plan-review r1)

- P1-05/P2-5/P3-7: `/account/delete` 가 09 의 토큰 CSS 를 쓰므로 Blocked by 에 09 추가(18 은 14 를 통해 09 에 전이 의존)
- P2-2/P3-2: Blocked by 에 11 추가(애플 secret 공개 접근자 소비)
- P3-9: CSRF 헬퍼를 01 로 옮겨 범위를 줄였고 분할선을 적어 둠 — 티켓 자체는 분할하지 않음(삭제 서비스·웹 페이지·revoke 가 한 흐름이라 수직 슬라이스 유지가 검증에 유리)

## 리뷰 노트 (plan-add r1)

- 16(법적 문서 보완)이 이 페이지 문구를 뒤에서 점검하므로 삭제 데이터 목록·방침 링크 조건 추가. Blocked by 변경 없음
