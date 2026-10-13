# 32: 앱 배포 — BASELINE 워크플로·fastlane·서명 복사·치환(`mobile/` 기준), develop→App Distribution/TestFlight, main→Play internal/TestFlight

**What to build:** `develop` 푸시로 Android APK 가 Firebase App Distribution 에, iOS 가 TestFlight 에 올라가고, `main` 푸시로 AAB 가 Play internal 트랙에, iOS 가 TestFlight 에 올라간다. BuildUrPalace 와 같은 구조를 복사해 식별자만 바꾼다. 사람 산출물(D0 Firebase 파일, D2 keystore·match)이 없어도 디버그 빌드와 CI 는 돈다.

**Blocked by:** 22

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §B.25, BASELINE, US 66. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] BASELINE 복사 목록(`~/.claude/baselines/buildurpalace.md`) 대로 `.github/workflows/flutter.yml`(`working-directory: mobile`), `mobile/android/fastlane/*`, `mobile/ios/fastlane/*`, `mobile/ios/ExportOptions.plist`, `mobile/android/app/build.gradle.kts` 서명·심볼 블록, `mobile/android/key.properties.example` 을 가져와 `com.dosaem.chosung`·Team `J8QUD7B666`·`FLUTTER_VERSION`·앱 이름으로 치환. AAB 스텝의 strip false-positive 처리 유지
- [ ] `mobile/ios/fastlane/app_privacy_details.json` 을 이 앱의 수집 항목(게스트 식별자, 이메일, 시도 기록, 구독, 광고 ID, 진단)으로 재작성
- [ ] 빌드에 `--dart-define=API_BASE_URL`(develop → develop 인스턴스 8090 도메인, main → prod), 광고 ID·`serverClientId` dart-define 전달
- [ ] flutter-ci.yml(22) 과 분리 유지, 러너 `self-hosted`. 필요한 GitHub secrets·match 레포·App Distribution 그룹을 `docs/RELEASE.md` 자기 절(없으면 만든다)에 표로
- [ ] 로컬 확인 조건: D0·D2 파일 없이 `flutter build apk --debug` 성공(Firebase 스킵 경로). `--release`·`build ipa` 는 "D0 Firebase 파일 + D2 keystore/match 가 있을 때" 로 전제를 적고 RELEASE.md 사람 체크로. 실제 푸시·업로드는 사람(D2)

## 리뷰 노트 (plan-review r1)

- P1-01/P2-1/P3-1: 모든 경로를 `mobile/` 기준으로 명시
- P1-16/P2-15/P3-12: release 빌드 조건을 D0·D2 전제로 분리, debug 빌드만 워커 조건
