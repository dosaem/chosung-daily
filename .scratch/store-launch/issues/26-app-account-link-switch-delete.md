# 26: 앱 계정 — 네이티브 구글/애플 연결·전환·백업 코드·삭제 다이얼로그

**What to build:** 플레이어가 내 기록 탭에서 구글(iOS·Android)·애플(iOS) 버튼으로 계정을 연결하거나 이미 연결된 기록으로 전환하고, Android 에서는 웹 백업 코드로 애플 계정 기록을 불러오며, 첫 완료 후 "연결하세요" 안내를 한 번 본다. 설정에서 계정 삭제를 확인 다이얼로그 후 실행하면 새 게스트로 돌아간다.

**Blocked by:** 10, 14, 25

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.6, §A.7, §B.21 S4 계정, US 18·18a·19·20·21·22. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] `google_sign_in` 7.x `authenticate()`(iOS 클라이언트 ID / Android `serverClientId` = 웹 클라이언트 ID) → `POST /auth/token-exchange`. `sign_in_with_apple`(iOS 만) → id_token + authorization_code 동봉. 성공 시 토큰 교체 → 홈·기록 재조회·로컬 상태 폐기
- [ ] AccountCard 상태: 미연결(버튼, Android 는 구글만) / 연결됨(provider 아이콘 + 마스킹 이메일 + "전환됨" 안내). `ACCOUNT_ALREADY_LINKED`·`INVALID_ID_TOKEN` 사용자 문구
- [ ] 백업 코드 입력 시트 → 기존 백업 코드 전환 API → 성공 시 전환(위젯 테스트)
- [ ] 첫 완료(S2) 후 연결 안내 1회(로컬 플래그)
- [ ] 삭제 다이얼로그(되돌릴 수 없음·구독 별도 해지 문구) → `DELETE /me` → 로컬 전부 삭제 → 새 게스트 발급 → 온보딩 완료 상태 유지
- [ ] 위젯 테스트: 플랫폼별 버튼 노출, 전환 후 재조회, 삭제 후 새 게스트. `audit.native` 통과
