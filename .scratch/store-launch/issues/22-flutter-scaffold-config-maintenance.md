# 22: Flutter 앱 골격(`mobile/`) — 테마·국제화·ApiClient 최소·게스트 발급·점검/업데이트 화면(S7)·CI

**What to build:** `mobile/` 에 Flutter 앱이 생기고, 실행하면 스플래시 → 게스트 토큰 발급/복원 → `/config` 확인 → 점검 중이면 점검 화면, 너무 오래된 버전이면 업데이트 화면, 아니면 3탭 홈 뼈대가 뜬다. 디자인 토큰(OVERRIDES)이 ThemeData 로 들어가 라이트/다크가 기기 설정을 따르고 UI 문구가 ko/en 으로 나온다. CI 에서 analyze·test 가 Firebase 설정 파일 없이도 돈다.

**Blocked by:** 03, 08

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §B.18~22, §C.31, SCREENS 탭 구조·S7, BASELINE. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] Flutter 루트는 **`mobile/`** 로 확정(레포 `app/` 은 Flask 패키지). 이후 32·33 의 `android/`, `ios/`, `integration_test/` 경로는 모두 `mobile/` 기준. flutter-ci 의 `working-directory: mobile`
- [ ] 패키지: Riverpod, go_router, dio, flutter_secure_storage, easy_localization(ko/en), sentry_flutter, firebase_core/analytics, flutter_native_splash, flutter_launcher_icons(임시 아이콘), very_good_analysis. 번들/패키지 `com.dosaem.chosung`, 앱 이름 "오늘의 초성"/"Hidden Vowels". Hive/freezed 없음
- [ ] Firebase 설정 파일(`google-services.json`, `GoogleService-Info.plist`)은 gitignore + `.example` 자리표시자 커밋, 파일이 없으면 Firebase 초기화를 건너뛴다(디버그·CI). analyze/test 는 파일 없이 통과
- [ ] `ApiClient` 인터페이스는 이 티켓이 쓰는 `POST /guests`, `GET /config`, `GET /me/stats` 만 정의 + Dio 구현 + 테스트용 Fake. 나머지 §A' 메서드는 쓰는 티켓(23·24·25·27·29·30)이 추가한다. `--dart-define=API_BASE_URL`. 에러 코드→도메인 예외 매핑 골격
- [ ] 게스트 토큰 secure storage 보관, 없으면 `POST /guests {puzzle_language}`(기기 언어가 en 이면 en). 401 이면 새 게스트
- [ ] OVERRIDES 토큰 → ThemeData(라이트/다크, Pretendard, Lucide), 토큰 이름을 상수로(`primaryButton`, `tileEmpty`, `tileCorrect`…), 그림자 없음. iPad 중앙 정렬 최대 600px 레이아웃 래퍼
- [ ] S7 점검/강제 업데이트 화면 + 분기(위젯 테스트: Fake `/config` 로 점검/업데이트/정상 3분기, 목업 없음 — 명세+토큰)
- [ ] 3탭 뼈대(오늘/순위/내 기록) + 탭 바 아래 배너 슬롯 자리(상시 예약, 내용은 29)
- [ ] `.github/workflows/flutter-ci.yml`(ubuntu-latest, analyze + test). `flutter analyze` 0건, `audit.native` 체크리스트 통과 기록
- [ ] README Flutter 절 초안(상태 흐름·SDK 선택·테스트 경계 각 한 단락)

## 리뷰 노트 (plan-review r1)

- P1-01/P2-1/P3-1: Flutter 루트 `mobile/` 확정, `app/` 선택지 삭제
- P1-09/P2-7: Blocked by 에 03 추가(`POST /guests {puzzle_language}` 소비)
- P1-14/P2-14: ApiClient 를 이 티켓이 쓰는 3개 메서드로 줄임 — 분할 대신 범위 축소
- P1-16/P2-15/P3-12: Firebase 파일 부재 시 초기화 스킵 + `.example` 전략
