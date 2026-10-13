# 11: 애플 client_secret 자동 갱신·만료 알림

**What to build:** 애플 로그인용 client_secret JWT(최대 180일)가 만료되기 전에 서버가 요청 경로에서 스스로 재서명해 150일 뒤 애플 로그인이 조용히 죽지 않는다. 운영자는 `/health` 로 만료 시각을 보고 7일 전 Slack 알림을 받는다. 웹(Services ID)·iOS(번들 ID) 두 secret 모두 대상.

**Blocked by:** 08, 10

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.13, §A.12, US 68. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] client_secret 접근자가 "<7일 남음이면 재서명 후 교체" 를 수행하고 `/auth/apple/login`·`/auth/apple/callback` 진입 시, 그리고 10 의 토큰 교환·14 의 revoke 경로에서 사용된다(프로세스별 자체 갱신, 외부 저장 없음)
- [ ] 테스트: 만료 6일 남은 secret 으로 login·callback 각각 호출 시 새 JWT 로 교체되고 Authlib 클라이언트의 `client_secret` 이 바뀐다
- [ ] `/health` 의 `apple_secret_expires_at` 이 채워진다(Services ID·번들 ID 중 더 이른 시각)
- [ ] Beat 주 1회: 7일 전이면 `notify_operator` 호출(테스트: 서비스 함수 직접 호출)
- [ ] README "설계 판단" 에 "애플 secret 요청 경로 갱신(Beat 재서명 대신)" 추가
