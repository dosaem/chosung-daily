# 27: 앱 계정 — 네이티브 구글/애플 연결·전환·백업 코드·삭제 다이얼로그

**What to build:** 플레이어가 내 기록 탭에서 구글(iOS·Android)·애플(iOS) 버튼으로 계정을 연결하거나 이미 연결된 기록으로 전환하고, Android 에서는 웹 백업 코드(= 게스트 토큰)로 애플 계정 기록을 불러오며, 첫 완료 후 "연결하세요" 안내를 한 번 본다. 설정에서 계정 삭제를 확인 다이얼로그 후 실행하면 새 게스트로 돌아간다.

**Blocked by:** 10, 14, 24, 25

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.6, §A.7, §B.21 S4 계정, US 18·18a·19·20·21·22. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] ApiClient 에 `POST /auth/token-exchange`, `DELETE /me` 추가(Dio + Fake)
- [ ] `google_sign_in` 7.x `authenticate()` — iOS 클라이언트 ID 는 `Info.plist`(`GIDClientID`)·URL scheme, Android `serverClientId`(= 웹 클라이언트 ID)는 `--dart-define` → `POST /auth/token-exchange`. `sign_in_with_apple`(iOS 만) → id_token + authorization_code 동봉. 성공 시 토큰 교체 → 홈·기록 재조회·로컬 상태 폐기
- [ ] 25 의 AccountCard 자리를 채움: 미연결(버튼, Android 는 구글만) / 연결됨(provider 아이콘 + 마스킹 이메일 + "전환됨" 안내). `ACCOUNT_ALREADY_LINKED`·`INVALID_ID_TOKEN` 사용자 문구
- [ ] 백업 코드 입력 시트: 입력값을 Bearer 로 `GET /me/stats` 호출 → 200 이면 secure storage 토큰 교체 + 로컬 상태 폐기 + 재조회. 전환 완료 = 22 의 게스트 토큰 Provider 값 교체(별도 이벤트 없음); 알림 재계산 연결은 28 이 그 Provider 를 구독해 붙인다, 401 이면 "올바르지 않은 백업 코드". **새 서버 엔드포인트를 만들지 않는다**(백업 코드 = 게스트 토큰, 웹 복원과 같은 규칙)
- [ ] 24 의 S2 연결 안내 자리에 첫 완료 후 1회 안내(로컬 플래그)
- [ ] 25 의 삭제 자리에 destructive 버튼 + 다이얼로그(되돌릴 수 없음·구독 별도 해지 문구) → `DELETE /me` → 로컬 전부 삭제 → 새 게스트 발급 → 온보딩 완료 상태 유지
- [ ] 위젯 테스트: 플랫폼별 버튼 노출, 전환 후 재조회, 백업 코드 200/401, 삭제 후 새 게스트. `audit.native` 통과, 목업 `e4_records`(AccountCard) 대비; 삭제 다이얼로그·백업 코드 시트는 목업 없음 — SCREENS S4 문구 + 토큰

## 리뷰 노트 (plan-review r1)

- P1-07/P2-6/P3-6: 존재하지 않는 "백업 코드 전환 API" 를 `GET /me/stats` 유효성 확인 방식으로 교체
- P2-3/P3-5: Blocked by 에 24·25 추가(S2 안내 자리, S4 호스트)
- P1-15/P2-17/P3-16: 참조 목업 `e4_records` 와 목업 없는 항목 명시
- P2-15: 클라이언트 ID 주입 방식(Info.plist / dart-define) 명시
- (r2) P1-26/P3-21: 완료 조건에서 28 산출물(알림 재계산 트리거) 요구를 빼고 22 의 게스트 토큰 Provider 교체만 남김 — 호출은 28 이 그 Provider 를 구독해 붙인다
