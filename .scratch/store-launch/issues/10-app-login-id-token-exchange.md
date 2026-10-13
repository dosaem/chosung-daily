# 10: 앱 로그인 — id_token 교환·aud 매트릭스·애플 refresh token 보관

**What to build:** 앱에서 네이티브 구글(iOS·Android)·애플(iOS) 로그인으로 받은 id_token 을 서버에 보내면 계정이 연결되거나 이미 연결된 기록으로 전환되고 새 게스트 토큰을 받는다. 애플은 authorization_code 도 함께 보내 서버가 refresh token 을 보관하므로 나중에 계정 삭제 때 애플 쪽 연결을 실제로 철회할 수 있다. 웹 애플 로그인도 같은 컬럼에 보관한다.

**Blocked by:** 01

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.6, ADR 0002, §A', 미정 17. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] `Account.provider_refresh_token`(Fernet, SECRET_KEY 파생 키), `Account.provider_client_id` 마이그레이션. 머지 직전 `flask db heads` 1개
- [ ] `clients/google_jwks.py`·`clients/apple.py`(JWKS 조회, 토큰 교환; revoke 래퍼는 14) 와 id_token 검증 순수 함수 분리. 테스트는 테스트 키 쌍으로 서명한 토큰을 진짜 검증(JWKS 는 monkeypatch)
- [ ] `POST /auth/token-exchange {provider, id_token, authorization_code?}` (Bearer) → aud 매트릭스(google iOS = iOS 클라이언트 ID, google Android = 웹 클라이언트 ID, apple = 번들 ID) 검증 → `link_or_switch_account` 재사용 → `{token}`. 실패 401 `INVALID_ID_TOKEN`, 이미 다른 게스트에 연결된 provider 계정은 전환(`existing` 경로), 현재 게스트에 다른 계정이 이미 있으면 `ACCOUNT_ALREADY_LINKED`
- [ ] apple 은 `authorization_code` 를 Apple 토큰 엔드포인트에서 교환(client_id = 번들 ID, client_secret = 번들 ID 용 JWT) → `refresh_token`·`provider_client_id` 저장, 교환 id_token 의 `sub` == 앱 id_token `sub` 확인(불일치 401). 재로그인·전환 시 두 컬럼 덮어쓰기. client_secret 생성은 현행 함수를 번들 ID 에도 쓸 수 있게 인자화(자동 갱신 접근자는 11)
- [ ] 웹 `/auth/apple/callback` 도 `refresh_token` 과 Services ID 를 같은 컬럼에 저장하도록 수정(기존 `test_oauth_routes.py` 통과)
- [ ] 설정값 `GOOGLE_IOS_CLIENT_ID`, `GOOGLE_WEB_CLIENT_ID`, `APPLE_APP_BUNDLE_ID`, 번들 ID 용 Apple key 설정을 `.env.example` 에 추가(미정 17 반영)
- [ ] README "설계 판단" 에 ADR 0002 요약(aud 매트릭스 표, 애플 토큰 보관 이유) 추가
