# 11: 애플 client_secret 자동 갱신·만료 알림

**What to build:** 애플 로그인용 client_secret JWT(최대 180일)가 만료되기 전에 서버가 요청 경로에서 스스로 재서명해 150일 뒤 애플 로그인이 조용히 죽지 않는다. 운영자는 `/health` 로 만료 시각을 보고 7일 전 Slack 알림을 받는다. 웹(Services ID)·iOS(번들 ID) 두 secret 모두 대상이며, 접근자는 공개 함수로 두어 14 의 revoke 경로가 재사용한다.

**Blocked by:** 08, 10

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.13, §A.12, US 68. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] client_secret 접근자(공개 함수, client_id 인자: Services ID | 번들 ID)가 "<7일 남음이면 재서명 후 교체" 를 수행하고 `/auth/apple/login`·`/auth/apple/callback` 진입과 10 의 토큰 교환 경로에서 사용된다(프로세스별 자체 갱신, 외부 저장 없음)
- [ ] 테스트: 만료 6일 남은 secret 으로 login·callback 각각 호출 시 새 JWT 로 교체되고 Authlib 클라이언트의 `client_secret` 이 바뀐다; 번들 ID 접근자도 같은 규칙
- [ ] `/health` 의 `apple_secret_expires_at` 이 채워진다(Services ID·번들 ID 중 더 이른 시각)
- [ ] Beat 주 1회: 7일 전이면 `notify_operator` 호출(테스트: 서비스 함수 직접 호출)
- [ ] README "설계 판단" 에 "애플 secret 요청 경로 갱신(Beat 재서명 대신)" 추가

## 리뷰 노트 (plan-review r1)

- P2-2/P3-2: "14 의 revoke 경로에서 사용" 을 완료 조건에서 빼고 접근자를 공개 함수로 두는 것으로 바꿈(14 가 이 티켓에 의존)
