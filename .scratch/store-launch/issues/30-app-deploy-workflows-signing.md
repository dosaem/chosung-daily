# 30: 앱 배포 — BASELINE 워크플로·fastlane·서명 복사·치환, develop→App Distribution/TestFlight, main→Play internal/TestFlight

**What to build:** `develop` 푸시로 Android APK 가 Firebase App Distribution 에, iOS 가 TestFlight 에 올라가고, `main` 푸시로 AAB 가 Play internal 트랙에, iOS 가 TestFlight 에 올라간다. BuildUrPalace 와 같은 구조를 복사해 식별자만 바꾼다.

**Blocked by:** 22

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §B.25, BASELINE, US 66. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] BASELINE 복사 목록(`~/.claude/baselines/buildurpalace.md`) 대로 `.github/workflows/flutter.yml`, `android/fastlane/*`, `ios/fastlane/*`, `ios/ExportOptions.plist`, `android/app/build.gradle.kts` 서명·심볼 블록, `android/key.properties.example` 을 가져와 `com.dosaem.chosung`·Team `J8QUD7B666`·`FLUTTER_VERSION`·앱 이름으로 치환. AAB 스텝의 strip false-positive 처리 유지
- [ ] `ios/fastlane/app_privacy_details.json` 을 이 앱의 수집 항목(게스트 식별자, 이메일, 시도 기록, 구독, 광고 ID, 진단)으로 재작성
- [ ] 빌드에 `--dart-define=API_BASE_URL`(develop → develop 인스턴스 8090 도메인, main → prod), 광고 ID dart-define 전달
- [ ] flutter-ci.yml(22) 과 분리 유지, 러너 `self-hosted`. 필요한 GitHub secrets·match 레포·App Distribution 그룹을 `docs/RELEASE.md` 표로
- [ ] 로컬 `flutter build apk --release`·`flutter build ipa`(서명 없이 가능한 범위) 성공 확인 기록. 실제 푸시·업로드는 사람(D2)
