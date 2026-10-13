# 22: Flutter 앱 골격 — 테마·국제화·ApiClient·게스트 발급·점검/업데이트 화면(S7)·CI

**What to build:** 앱이 실행되면 스플래시 → 게스트 토큰 발급/복원 → `/config` 확인 → 점검 중이면 점검 화면, 너무 오래된 버전이면 업데이트 화면, 아니면 3탭 홈 뼈대가 뜬다. 디자인 토큰(OVERRIDES)이 ThemeData 로 들어가 라이트/다크가 기기 설정을 따르고 UI 문구가 ko/en 으로 나온다. CI 에서 analyze·test 가 돈다.

**Blocked by:** 08

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §B.18~22, §C.31, SCREENS 탭 구조·S7, BASELINE. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] `app/`(또는 `mobile/`) 에 Flutter 프로젝트: Riverpod, go_router, dio, flutter_secure_storage, easy_localization(ko/en), sentry_flutter, firebase_core/analytics, flutter_native_splash, flutter_launcher_icons(임시 아이콘), very_good_analysis. 번들/패키지 `com.dosaem.chosung`, 앱 이름 "오늘의 초성"/"Hidden Vowels". Hive/freezed 없음
- [ ] `ApiClient` 인터페이스(§A' 1:1 메서드) + Dio 구현 + 테스트용 Fake. `--dart-define=API_BASE_URL`. 에러 코드→도메인 예외 매핑
- [ ] 게스트 토큰 secure storage 보관, 없으면 `POST /guests`(기기 언어가 en 이면 en 선호). 401 이면 새 게스트
- [ ] OVERRIDES 토큰 → ThemeData(라이트/다크, Pretendard, Lucide), 토큰 이름을 상수로(`primaryButton`, `tileEmpty`, `tileCorrect`…), 그림자 없음. iPad 중앙 정렬 최대 600px 레이아웃 래퍼
- [ ] S7 점검/강제 업데이트 화면 + 분기(위젯 테스트: Fake `/config` 로 점검/업데이트/정상 3분기)
- [ ] 3탭 뼈대(오늘/순위/내 기록) + 탭 바 아래 배너 슬롯 자리(상시 예약, 내용은 28)
- [ ] `.github/workflows/flutter-ci.yml`(ubuntu-latest, analyze + test). `flutter analyze` 0건, `audit.native` 체크리스트 통과 기록
- [ ] README Flutter 절 초안(상태 흐름·SDK 선택·테스트 경계 각 한 단락)
