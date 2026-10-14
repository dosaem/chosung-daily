# mobile — 오늘의 초성 / Hidden Vowels (Flutter)

같은 Flask 서버(`/api/v1`)를 쓰는 iOS·Android 앱. 설계 판단(상태 흐름·SDK 선택·
테스트 경계)은 레포 루트 [`README.md`](../README.md) "설계 판단 > 22" 에 있다.

## 실행

```bash
flutter pub get
flutter run --dart-define=API_BASE_URL=http://localhost:8000/api/v1
```

`API_BASE_URL` 을 안 넘기면 Android 에뮬레이터에서 호스트를 가리키는
`http://10.0.2.2:8089/api/v1` 을 쓴다(`lib/config/app_env.dart`).
Sentry 를 켜려면 `--dart-define=SENTRY_DSN=<DSN>` 을 같이 넘긴다 — 비어 있으면
초기화하지 않는다.

Firebase 설정 파일(`android/app/google-services.json`,
`ios/Runner/GoogleService-Info.plist`)은 커밋하지 않는다. **파일이 없으면
빌드에서 Gradle 플러그인을 건너뛰고 런타임 초기화도 건너뛰므로**, 새로 클론한
상태 그대로 분석·테스트·디버그 실행이 된다. 넣는 방법은
[`docs/RELEASE.md`](../docs/RELEASE.md) "22. Flutter 앱 골격".

## 검사

```bash
dart format --set-exit-if-changed lib test
flutter analyze    # 0건이어야 한다
flutter test
```

CI 는 `.github/workflows/flutter-ci.yml`(ubuntu-latest, `mobile/` 작업 디렉터리).

## 구조

```
lib/
├── api/        # ApiClient 인터페이스 + Dio 구현 + 응답 모델 + 에러 매핑
├── config/     # dart-define 값, Firebase·Sentry 부트스트랩, provider 재시도 정책
├── guest/      # 게스트 토큰 저장소(secure storage) + 앱 전역 provider
├── startup/    # 시작 흐름(토큰 → /config → 분기), 버전 비교·분기 판단 순수 함수
├── routing/    # go_router 설정 + 리다이렉트 순수 함수
├── theme/      # OVERRIDES 토큰 → ThemeData (라이트/다크)
├── screens/    # 스플래시, 점검·강제 업데이트(S7), 3탭 홈 뼈대
├── widgets/    # 최대 600px 본문 래퍼, 배너 슬롯, 스켈레톤
└── l10n/       # 지원 로케일(ko/en). 문구는 assets/translations/*.json
```

자산: `assets/fonts/` Pretendard(OFL, 라이선스 동봉), `assets/icon/` 임시 아이콘
(생성 스크립트 `tool/make_placeholder_icon.py`, 최종본은 티켓 33).
