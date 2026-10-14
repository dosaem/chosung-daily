# 티켓 27 구현 증거 — S3 순위 · S4 내 기록(streak·7일 그리드·설정 리스트 뼈대)

**브랜치:** `dosaem/t27-app-leaderboard-records-settings` · **날짜:** 2026-10-14
**범위:** Flutter 앱(`mobile/`) + README "설계 판단" `### 27.` 한 절. 백엔드·웹·
마이그레이션은 한 줄도 건드리지 않았다(`/puzzles/today/leaderboard`·`/me/history`
는 티켓 07 이 이미 만든 것을 앱이 부르기만 한다).

## 0. 한 줄 요약

S3 를 익명 리더보드 + 내 순위(21위 밖 하단 고정)로, S4 를 streak 3칸 + 7일 그리드 +
설정 리스트(퍼즐 언어·법적 문서·라이선스·버전)로 채우고 28~32 가 채울 자리 8개를
키로 고정했다. 앱 테스트 259개 통과(이 티켓이 더한 건 57개, 골든 4장 포함),
백엔드 1110개 통과, `flutter analyze` 0건 · `dart format` 변경 없음 · `ruff` 통과.

## 1. 티켓 체크박스 ↔ 증거

| 체크박스 | 증명하는 테스트/명령 | 위치 |
|---|---|---|
| ApiClient 에 `GET /puzzles/today/leaderboard`, `GET /me/history` 추가(Dio + Fake) | `test/api/dio_api_client_test.dart` "순위·기록 엔드포인트" 4개(경로·쿼리·Bearer·404 `NO_PUZZLE_TODAY`·토큰 없음), `test/api/api_models_test.dart` `Leaderboard.fromJson`·`HistoryDay.fromJson` 4개, `test/fakes/fake_api_client.dart` 확장 | §3.1 |
| S3: 언어 칩 표시 전용 · `entries` 리스트(내 행 강조) · 21위 밖 `me` 하단 고정 · 빈 상태 문구 | `test/screens/ranking_tab_test.dart` 11개("정상", "내 행은 강조된다", "21위 밖이면 내 행을 목록 하단에 고정한다", "상위 목록에 내 행이 있으면 하단 고정 행은 없다", "빈 리더보드…", "오늘 퍼즐이 아직 없으면 오류가 아니라 빈 상태다" 등) | §3.2 |
| S4: StreakBadge 3칸 · 7일 그리드(4종) · 설정 리스트(퍼즐 언어 → `PATCH /me` 후 홈 재조회, 법적 문서 웹 링크, 라이선스, 버전) · 자리 8개에 담당 번호 주석 | `test/screens/records_tab_test.dart` 10개, `test/records/history_grid_test.dart` 4개, `test/settings/puzzle_language_controller_test.dart` 5개, `test/settings/legal_links_test.dart` 3개 | §3.3 |
| 위젯 테스트: 리더보드 `me` 행 · 빈 상태 · 7일 그리드 · 퍼즐 언어 변경 후 재조회 | 위 네 묶음 중 "21위 밖…", "빈 리더보드…", "7일 그리드는…", "퍼즐 언어를 바꾸면 PATCH /me 뒤 홈을 다시 읽는다" | §3.2·§3.3 |
| 퍼즐 언어 쓰기 직렬화·늦은 응답 버리기(코디네이터 메모) | `test/settings/puzzle_language_controller_test.dart` "바꾸는 중에는 다음 요청을 받지 않는다", `test/screens/records_tab_test.dart` "바꾸는 동안 퍼즐 언어 행은 다시 눌리지 않는다" | §3.3 |
| 태블릿 T3·T4(폭 390/744/1024, 설정 자리의 열 고정) | `test/screens/ranking_records_tablet_test.dart` 7개 | §3.4 |
| `audit.native`(태블릿 폭 포함) 통과 · 목업 `e3_leaderboard`·`e4_records` 대비 기록 | §4 체크리스트, §5 골든 4장 | §4·§5 |

마이그레이션을 만들지 않았으므로 `flask db heads` 는 해당 없음(`migrations/`
변경 0건 — §2 의 파일 목록 참고).

## 2. 바뀐 파일

**새로 만든 것**

| 파일 | 역할 |
|---|---|
| `mobile/lib/ranking/leaderboard_controller.dart` | S3 상태. 값이 `null` = "오늘 그 언어 퍼즐 없음"(오류 아님), `retry()` |
| `mobile/lib/records/history_controller.dart` | `GET /me/history?days=7` 한 번 읽는 `FutureProvider` |
| `mobile/lib/records/history_grid.dart` | `combinedDayResult` — 하루의 ko/en 결과를 streak 과 같은 기준으로 한 칸에 합치는 순수 함수 |
| `mobile/lib/settings/puzzle_language_controller.dart` | 퍼즐 언어 `Notifier`. `PATCH /me` 성공 시 오늘 퍼즐·리더보드 무효화 |
| `mobile/lib/settings/legal_links.dart` | `legalDocumentUrl`(순수 함수) + `webLinkLauncherProvider`(테스트 seam) |
| `mobile/lib/widgets/leaderboard_row.dart` | OVERRIDES §6 `LeaderboardRow` — 4칸(순위·이름·시도·시간), 내 행 `brand-subtle` |
| `mobile/lib/widgets/seven_day_grid.dart` | `SevenDayGrid` + `DayCell`(성공 체크 / 실패 X / 진행 중 brand 고리 / 미플레이 빈 면) |
| `mobile/lib/widgets/settings_row.dart` | 설정 한 줄(라벨·값·화살표). `onTap == null` 이면 뒤 티켓이 채울 자리 |
| `mobile/test/...` 7개 + 골든 4장 | §3 |

**고친 것**

| 파일 | 변경 |
|---|---|
| `mobile/lib/api/api_models.dart` | `Leaderboard`·`LeaderboardEntry`·`MyRank`·`HistoryDay`·`DayResult` 추가 |
| `mobile/lib/api/api_client.dart` | `fetchTodayLeaderboard`·`fetchMyHistory` 선언 |
| `mobile/lib/api/dio_api_client.dart` | 두 메서드 구현(`/me/history` 만 최상위가 배열이라 `_send<List<dynamic>>`) |
| `mobile/lib/screens/ranking_tab.dart` | 뼈대 → S3 전체(T3 넓은 표 포함) |
| `mobile/lib/screens/records_tab.dart` | 뼈대 → S4 전체(T4 2열 + `RecordsSlot` 키 8개) |
| `mobile/assets/translations/{ko,en}.json` | `language`·`ranking`·`records` 사전 추가 |
| `mobile/test/fakes/fake_api_client.dart` | 두 호출의 가짜 응답·호출 기록·에러 주입 |
| `README.md` | "설계 판단" 끝에 `### 27.` 한 절(공통 규칙대로 자기 번호 소제목만 추가) |

`.env.example`·`docs/RELEASE.md`·스펙 "미정 항목" 은 더할 내용이 없어 건드리지 않았다.

## 3. 테스트 (무엇을 증명하는가)

### 3.1 API 경계 — `test/api/` (+8개, 파일 합계 36개)

- `GET /puzzles/today/leaderboard` 가 `limit=20` 만 붙고 **`language` 는 안 붙는다**
  (서버가 게스트 선호 언어로 고른다 — README `### 27.`), Bearer 가 붙는다.
- 그 언어의 오늘 퍼즐이 없으면 404 `NO_PUZZLE_TODAY` → `NoPuzzleTodayApiException`.
- `GET /me/history` 가 `days=7` 을 붙이고 **배열** 응답을 날짜 목록으로 읽는다.
- 토큰이 없으면 두 호출 다 서버까지 가지 않는다(어댑터에 요청 0건).
- 모델: `me: null`·빈 `entries`, 모르는 언어 키는 버리고 모르는 결과 값은
  `none` 으로 눕힌다.

### 3.2 S3 순위 — `test/screens/ranking_tab_test.dart` (11개)

날짜·칩·목록·내 순위 카드 / 내 행 강조(`isMe`) / **21위 밖 하단 고정**(entries 20줄 +
`me` 23위 → 고정 행이 화면 안에 있다) / 상위에 내 행이 있으면 고정 행 없음 /
"아직 안 풀었어요" / 빈 상태 문구(OVERRIDES §7) / 퍼즐 없음도 빈 상태 / 스켈레톤
(스피너 0개) / 오류 카드 + 재시도가 실제로 다시 읽는다 / 오프라인 배너 / en UI.

### 3.3 S4 내 기록 — `test/screens/records_tab_test.dart` (11개) + 순수 함수·컨트롤러 (12개)

- streak 3칸(현재 12일 · 최고 30일 · 누적 41문제).
- 7일 그리드 7칸이 `success/fail/success/none/success/fail/inProgress` 로 칠해진다
  — 한 언어만 풀어도 성공, 끝나지 않은 언어가 있으면 진행 중(`history_grid_test`
  4개가 같은 규칙을 단위로 고정).
- 기록을 못 읽으면 그 자리만 한 줄 + 재시도(화면 전체가 오류로 덮이지 않는다).
- 설정 리스트에 퍼즐 언어(값 "한국어")·개인정보처리방침·이용약관·오픈소스
  라이선스·버전(1.2.3)이 있다.
- **퍼즐 언어 변경**: 행 → 피커 → "영어" → `PATCH /me` 1회 + 오늘 퍼즐 재조회
  (`fetchTodayPuzzleCalls` 1 → 2). 컨트롤러 테스트가 리더보드 재조회까지 본다.
- 변경 실패(네트워크)면 행 아래 빨간 한 줄이 남고 값은 그대로.
- **쓰기 직렬화**: 응답을 `Completer` 로 잡아 두면 그 동안 행이 비활성이고
  (`onTap == null`) 두 번째 요청은 서버로 나가지 않는다. 세대 번호로 늦게 온
  응답을 버린다(티켓 25 `TodayPuzzleNotifier` 와 같은 방식).
- 법적 문서는 `…/privacy?lang=ko`·`…/terms?lang=ko` 로 연다(가짜 launcher 가 받은
  URL 을 그대로 확인). `legal_links_test` 3개가 URL 조립을 단위로 고정.
- 오픈소스 라이선스 → `LicensePage` 가 열린다.
- 자리 8개가 다 있고 **키 있는 행은 전부 `onTap == null`**(28~32 전까지 비활성).
- en UI 에서도 같은 화면.

### 3.4 태블릿 T3·T4 — `test/screens/ranking_records_tablet_test.dart` (7개)

실제 셸(`AdaptiveScaffold`) 안에서 390 / 744 / 1024 를 돌린다.

| 폭 | S3 | S4 |
|---|---|---|
| 390 | 머리글 없음, 내 순위 카드는 날짜 줄 **아래** | 1열(계정 자리와 알림 자리의 x 중심이 같고 세로로 이어진다) |
| 744 | 4열 표 머리글(순위·이름·시도·시간), 내 순위 카드가 날짜와 **한 줄** 오른쪽 | 아직 1열, 그리드 폭 ≤600 |
| 1024 | 표 폭 ≤840, 21위 밖 고정 행 유지 | **2열** — 계정·구독·백업 코드는 왼쪽, 일일 알림·리마인더·광고 개인정보·하는 법·계정 삭제는 오른쪽(T4 그대로), 열 폭 ≤480 |

마지막 테스트는 1024 → 390 으로 좁혀도 자리들이 사라지지 않고 한 열로 합쳐지는
것까지 본다(회전·Split View).

## 4. `audit.native` 체크리스트 (impeccable `reference/audit.native.md`)

22·24·25 와 같은 방식이다 — 브라우저 도구·`impeccable detect` 는 HTML/CSS 용이라
쓰지 않고, 소스를 `reference/ios.md`·`android.md` 기준으로 읽고 5축에 점수를
매긴다. 폭 확인은 눈이 아니라 위젯 테스트(390·744·1024)와 골든 4장이다.

| # | 축 | 25 | 27 | 핵심 소견 |
|---|---|---|---|---|
| 1 | Accessibility | 4 | 4 | 리더보드 한 줄이 "N위 {이름}, 시도 N회, 걸린 시간 HH:MM:SS" 한 덩어리로 읽힌다(칸 4개가 따로 읽히면 어느 줄인지 모른다). 7일 그리드는 칸마다 "10월 13일 성공" 으로 읽고, 색만으로 구분하지 않게 성공=체크·실패=X·진행 중=고리·미플레이=빈 면으로 모양을 나눴다. 설정 행은 최소 높이 44(OVERRIDES §4), 비활성 행은 화살표를 빼서 색 외에도 알 수 있다. 스켈레톤은 `ExcludeSemantics` |
| 2 | Performance | 3 | 3 | 리더보드는 `ListView.separated`(최대 20줄이지만 목록이라 가상화 경로를 쓴다), 7일 그리드는 7칸 고정. 언어 변경은 `invalidate` 1회로 두 provider 만 다시 읽는다 |
| 3 | Appearance & Theming | 4 | 4 | 새 위젯 전부 `AppColors` 토큰만 쓴다(raw hex 는 여전히 `app_colors.dart` 한 파일뿐). 내 행 강조는 `brand-subtle` 면 — brand 는 고리 테두리에만 썼다(OVERRIDES §2 "면 채움·일반 글자색 금지") |
| 4 | Platform Conformance | 3 | 3 | Material 기본 컨트롤(`ListView`·`RadioGroup`+`RadioListTile`·`InkWell`·`showLicensePage`), 언어 피커는 폭에 따라 시트/다이얼로그(T2 `showAdaptiveSheet`). 외부 링크는 `LaunchMode.externalApplication` |
| 5 | Adaptivity | 4 | 4 | T3 표(≤840)·T4 2열(각 ≤480)·medium 1열(600)·폭 왕복 유지. 2열은 열마다 따로 스크롤돼 설정이 길어져도 기록이 밀리지 않는다 |
| **합계** | | **18/20** | **18/20** | **Excellent (minor polish)** |

**추가 항목 "태블릿 폭(744·1024·1366) 포함": 통과.** 744·1024 는 이 티켓의 태블릿
테스트가, 1366·834·320 은 24 의 셸 테스트가 덮는다(이 티켓 테스트도 `AdaptiveScaffold`
안에서 돈다).

### 디자인 파일과 다르게 구현한 곳 (커밋 메시지에도 적는다)

1. **리더보드 이름이 "게스트 #a3f1" 이다.** 목업 `e3_leaderboard` 는 이메일·닉네임을
   보여주지만 스펙 §A'·README "07. 리더보드 익명 표시" 가 익명 표시를 못 박았다.
2. **1~3위를 brand 색이 아니라 굵은 글자로.** 목업은 상위 3명의 순위 숫자를
   주황색으로 쓴다 — OVERRIDES §2 와 SCREENS S3("brand 색 글자 금지")를 따랐다.
3. **표 머리글은 medium 이상에서만.** 목업은 폰에도 머리글이 있지만 SCREENS T3 가
   "medium 이상 넓은 표" 로 규정했고, 폰 한 줄은 "1회"·"00:00:41" 자체가 단위를
   말한다. 폰에서 머리글을 빼면 20줄 중 한 줄이 더 보인다.
4. **S4 상단에 화면 제목을 두지 않았다.** 목업 `e4_records` 에는 "내 기록" 제목과
   설정 톱니가 있지만 SCREENS S4 본문과 T4 와이어는 streak 3칸으로 시작한다
   (탭 바·rail 이 이미 "내 기록" 이라고 말한다). 톱니는 설정이 이 화면 자체라 뺐다.
5. **미플레이 칸에 헤어라인을 둘렀다.** `muted` 면은 `background` 와 밝기가 거의
   같아 라이트 모드에서 칸이 사라져 보였다(골든으로 확인). 목업 `e4_records` 의
   마지막 빈 고리와 같은 모양이 되게 `border` 1px 을 더했다.
6. **참가자 수("1,420명")는 넣지 않았다.** 목업 상단 통계는 `/puzzles/today/stats`
   쪽이고 S3 명세에 없다 — 결과 시트(티켓 26)가 쓰는 값이다.

### 남은 결함 / 의도된 이탈

| 심각도 | 위치 | 내용 | 받는 곳 |
|---|---|---|---|
| P2 | `RecordsSlot` 8개 | 계정·구독·백업 코드·일일 알림·리마인더·광고 개인정보·하는 법·계정 삭제가 **비활성 행**이다("준비 중"). 이 티켓의 범위가 자리까지다 | 28·29·30·31·32 |
| P3 | 순위 탭 | 탭 재진입·포그라운드 복귀 때 자동 재조회하지 않는다(언어 변경·재시도만). 근거는 README `### 27.` "알려진 제한" | — (의도) |
| P3 | 7일 그리드 | 한 칸이 두 언어를 합친 결과라 "ko 는 풀고 en 은 실패" 를 칸만 보고는 구분할 수 없다. SCREENS T4 가 칸 하나라 그대로 뒀고, 합치는 기준은 streak 과 같다 | — (의도) |
| P2 | — | 시뮬레이터·실기기 스크린샷은 없다. 골든은 테스트 렌더러다 | 티켓 35·36 |

## 5. 목업 대비 기록 (골든 4장)

`mobile/test/golden/`, 갱신은 `flutter test test/golden --update-goldens`.
Pretendard·Lucide 를 실제로 불러와 찍는다.

| 골든 | 대조 대상 | 결과 |
|---|---|---|
| `ranking_light_390.png` | `design/stitch/e3_leaderboard.png` | 날짜 + 칩 → 내 순위 카드 → 순위·이름·시도·시간 5줄 → 하단 고정 "23 나" 까지 같은 순서. 다른 점은 위 1·2·3·6 |
| `ranking_tablet_1024.png` | SCREENS T3 와이어 | rail + "10월 13일 [한국어]" 좌측 · 내 순위 카드 우측 · 4열 표(폭 840 가운데) · 하단 고정 행 |
| `records_light_390.png` | `design/stitch/e4_records.png` | streak 3칸 → "최근 7일" 7칸 → 계정·구독·백업 코드 자리 → 설정 리스트 → (스크롤 아래) 계정 삭제. 다른 점은 위 4·5 |
| `records_tablet_1024.png` | SCREENS T4 와이어 | 왼쪽 열 = streak·7일·계정·구독·백업 코드, 오른쪽 열 = 설정 리스트·계정 삭제(destructive). 열 폭 ≤480 |

## 6. 검증 (실제 실행 명령과 출력)

### 6.1 앱 테스트 (전체)

```
$ cd mobile && flutter test
00:16 +259: All tests passed!
```

이 티켓이 더한 테스트 57개(파일별로 따로 돌린 결과):

```
test/api/api_models_test.dart                   -> +16 (기존 12 + 4)
test/api/dio_api_client_test.dart               -> +20 (기존 16 + 4)
test/records/history_grid_test.dart             -> +4
test/settings/legal_links_test.dart             -> +3
test/settings/puzzle_language_controller_test.dart -> +5
test/ranking/leaderboard_controller_test.dart   -> +4
test/screens/ranking_tab_test.dart              -> +11
test/screens/records_tab_test.dart              -> +11
test/screens/ranking_records_tablet_test.dart   -> +7
test/golden/ranking_records_golden_test.dart    -> +4
```

### 6.2 앱 정적 분석·포맷 (CI `flutter-ci.yml` 과 같은 명령)

```
$ cd mobile && flutter analyze
Analyzing mobile...
No issues found! (ran in 2.4s)

$ cd mobile && dart format --output=none --set-exit-if-changed lib test
Formatted 85 files (0 changed) in 0.20 seconds.   # exit 0
```

### 6.3 백엔드 테스트 (전용 자원)

```
$ TEST_DATABASE_URL='mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t27?charset=utf8mb4' \
  TEST_REDIS_URL='redis://localhost:6379/15' \
  TEST_MIGRATION_DATABASE_URL='mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t27_migrations?charset=utf8mb4' \
  uv run pytest -q
1110 passed in 723.59s (0:12:03)
```

DB `chosung_daily_test_t27` / `_migrations` 는 이 티켓 전용으로 새로 만들었고
(`CREATE DATABASE … ; GRANT ALL ON … TO 'chosung'@'%'`), Redis 는 DB 15 를 썼다.
공용 테스트 DB·Redis 는 건드리지 않았다.

### 6.4 백엔드 린트

```
$ uv run ruff check .
All checks passed!

$ TEST_DATABASE_URL=… (chosung_daily_test_t27) \
  TEST_REDIS_URL=… (redis DB 15) \
  TEST_MIGRATION_DATABASE_URL=… (chosung_daily_test_t27_migrations) \
  uv run pytest -q
1257 passed in 879.68s (0:14:39)                   # exit 0
# 1110 → 1257 은 main 의 티켓 16 병합이 더한 테스트다(이 티켓은 백엔드 0건).
# 전용 DB·Redis DB 15 만 썼고 공용 테스트 DB 는 건드리지 않았다.
# 접속 문자열의 인증 값은 이 문서에 옮기지 않는다.
```

### 6.5 마이그레이션

`migrations/` 변경 0건이라 `flask db heads` 는 해당 없음(이 티켓은 앱 전용).

### 6.6 네이티브 빌드 (코디네이터 메모 요청)

```
$ cd mobile && flutter build ios --no-codesign --debug
Running pod install...                                              4.5s
Running Xcode build...
Xcode build done.                                           59.7s
✓ Built build/ios/iphoneos/Runner.app          # exit 0

$ cd mobile && flutter build apk --debug
The operation couldn't be completed. Unable to locate a Java Runtime.
Gradle task assembleDebug failed with exit code 1                    # exit 1
```

**Android 빌드는 이 머신에서 못 돌린다 — 코드 문제가 아니다.**
`flutter doctor` 가 `[!] Android toolchain … ✗ Could not determine java version`,
`/usr/libexec/java_home` 가 "Unable to locate a Java Runtime" 를 준다(JDK 가 설치돼
있지 않다). 이 티켓은 Dart 코드·번역 JSON 만 바꿨고 Gradle·Podfile·플러그인·권한은
0건이라 Android 쪽에 새로 깨질 거리가 없고, iOS 빌드가 같은 Dart 코드를 실제로
컴파일해 통과했다. 코디네이터에게도 보고한다.

빌드 뒤 `mobile/build`(572M)와 `mobile/ios/Pods`(68M)를 지웠고, `pod install` 이
건드린 `ios/Runner.xcodeproj/project.pbxproj`·`Runner.xcworkspace/contents.xcworkspacedata`
는 원래대로 되돌리고 생성된 `ios/Podfile.lock` 도 지웠다(레포가 추적하지 않는 파일들
— 작업 트리는 clean 이다).

### 6.7 안 한 것

- **실기기·시뮬레이터 확인, 스크린 리더 실제 낭독 확인**은 하지 않았다(티켓 35·36).
- `impeccable detect` 는 웹 전용이라 이 티켓에선 돌리지 않았다(§4).

## 7. 리베이스

로컬 `main`(24c584d) 위로 리베이스했다 — 충돌 없음. `origin` 에는 push 하지
않았다. main 의 새 커밋 2개(381ea78·24c584d)는 `.scratch/` 계획 문서만 바꿔서
백엔드 테스트(§6.3)는 리베이스 전 결과가 그대로 유효하다.

## 8. 리베이스 후 재확인

```
$ git rebase main
Successfully rebased and updated refs/heads/dosaem/t27-app-leaderboard-records-settings.

$ cd mobile && flutter test
00:16 +259: All tests passed!

$ cd mobile && flutter analyze
Analyzing mobile...
No issues found! (ran in 3.9s)

$ git status --short     # (출력 없음 — 작업 트리 clean)
$ git log --oneline main..HEAD
수정 27-5: 퍼즐 언어 쓰기 직렬화 + 늦은 응답 버리기
구현 27-4: 태블릿 T3·T4 테스트·골든 4장·README 설계 판단·구현 증거
구현 27-3: S4 내 기록 — streak 3칸·7일 그리드·설정 리스트와 28~32 의 자리
구현 27-2: S3 순위 — 익명 리더보드·내 순위·21위 밖 하단 고정
구현 27-1: ApiClient 에 리더보드·최근 기록 추가
```

(리베이스 뒤에 27-5 와 이 문서 수정이 더 들어갔다. 최신 해시는
`git log --oneline main..HEAD` 로 본다.)

## 수정 라운드 1

리뷰 라운드 1(`review/impl-review-27.md`, 판정 FAIL — MAJOR 2 / MINOR 2)의 결함
4건을 전부 고쳤다. 각 결함은 **리뷰의 재현 입력을 먼저 실패하는 테스트로 고정한
뒤**(아래 "재현(red)" 출력) 원인을 고쳤다. 리뷰 파일은 고치지 않았다.
수정 커밋: `수정 27-6: 플레이 결과 뒤 순위·기록 갱신, 로딩/스크롤 적응성 결함`.

### D-27-1 (MAJOR) — 정답 제출 뒤 내 순위를 갱신할 수 없음

- **원인:** 오늘이 끝났다는 사실이 다른 탭의 데이터로 전달되지 않는다.
  `leaderboardProvider` 는 최초 응답을 보관하고, 재조회 경로는 오류 재시도와 언어
  변경뿐이었다. 셸(`StatefulShellRoute`)이 세 탭을 다 살려 두므로 탭 재진입은
  위젯 재빌드일 뿐 provider 재조회가 아니다 — 순위를 먼저 본 사람은 "아직 안
  풀었어요" 를 앱 재시작까지 본다.
- **수정:** `TodayPuzzleNotifier.submit` 이 제출 결과로 오늘이 끝나면
  (`played.status.isFinished`) `_invalidateDayResultReaders()` 로
  `leaderboardProvider`·`historyProvider` 를 무효화하고 내 기록 숫자를 다시 읽는다
  (`mobile/lib/puzzle/today_puzzle_controller.dart`). 끝나지 않은 시도 한 줄로는
  부르지 않는다 — 순위는 푼 사람만 올라간다. 25 의 세대(`_generation`) 구조와
  제출 중 재조회 보류(`_refreshQueued`)는 건드리지 않았고, 무효화는 제출 응답을
  상태에 쓴 **뒤** 한 번만 돈다.
- **증명:** `mobile/test/screens/play_result_refresh_test.dart`
  "D-27-1: 순위를 먼저 본 뒤 정답을 제출하면 내 순위가 갱신된다" — 실제
  `ChosungApp`·라우터·탭 탭(tap)으로 리뷰의 입력 순서를 그대로 밟는다.

```
# 재현(red) — 고치기 전
$ cd mobile && flutter test --no-pub test/screens/play_result_refresh_test.dart
Expected: <2>                     # api.fetchTodayLeaderboardLimits.length
  Actual: <1>
00:04 +1 -3: Some tests failed.

# 고친 뒤(green)
00:00 +3: test/screens/play_result_refresh_test.dart: D-27-1: 순위를 먼저 본 뒤 정답을 제출하면 내 순위가 갱신된다
```

### D-27-2 (MAJOR) — 내 기록의 streak·누적·7일 그리드가 플레이 결과를 반영하지 않음

- **원인:** 두 갈래다. ① `historyProvider` 는 재시도 버튼 외에 무효화 경로가 없다.
  ② streak 3칸은 `startupStatsProvider`(앱 시작 때 읽은 `/me/stats` snapshot)를
  읽는다 — **무효화로는 고칠 수 없다.** 다시 빌드하면 같은 시작 snapshot, 즉 플레이
  전 숫자로 돌아간다. 그래서 제출 후 내 기록을 **처음** 열어도 이전 값이 보였다.
- **수정:** ① D-27-1 과 같은 경로에서 `historyProvider` 를 무효화한다.
  ② `mobile/lib/records/my_stats_controller.dart` 를 새로 두었다 — 시작 snapshot 을
  첫 값으로 쓰고(추가 호출 0회), `refresh()` 가 서버에서 다시 읽는다. 실패하면 보던
  숫자를 그대로 둔다(OVERRIDES §7 — 숫자 하나로 화면을 오류로 덮지 않는다). 응답
  경합은 25 와 같은 세대 번호로 끊는다. S4 streak 카드와 S1 `StreakBadge` 가 같이
  읽는다 — 한쪽만 바꾸면 같은 순간에 두 탭이 다른 streak 을 말한다.
- **증명:** 같은 파일의 "D-27-2: 내 기록을 먼저 본 뒤 정답을 제출하면 streak·누적·
  7일이 갱신된다", "D-27-2: 제출 뒤 내 기록을 처음 열어도 갱신된 streak 이 보인다",
  그리고 `mobile/test/records/my_stats_controller_test.dart`(3개 — 첫 값은 시작
  snapshot·추가 호출 0회 / refresh 는 다시 읽는다 / refresh 실패 시 보던 숫자 유지).

```
# 재현(red) — 고치기 전
Expected: <2>                               # api.fetchMyHistoryDays.length
  Actual: <1>
Expected: exactly 2 matching candidates     # "1일"(현재·최고)
  Actual: _TextWidgetFinder:<Found 0 widgets with text "1일": []>

# 고친 뒤(green)
00:01 +4: … D-27-2: 내 기록을 먼저 본 뒤 정답을 제출하면 streak·누적·7일이 갱신된다
00:01 +5: … D-27-2: 제출 뒤 내 기록을 처음 열어도 갱신된 streak 이 보인다
00:00 +3: test/records/my_stats_controller_test.dart: (3개 통과)
```

**역방향도 고정했다:** "끝나지 않은 제출은 순위·기록을 다시 읽지 않는다" — 오답 한
줄에 세 엔드포인트를 다시 읽지 않는다(세 호출 횟수 모두 1).

### D-27-3 (MINOR) — S4 1열↔2열 전환 시 스크롤 위치 소실

- **원인:** 폭 분기가 스크롤 위젯 트리를 교체하는데 위치를 저장할 키가 없어서 새
  `Scrollable` 이 0 에서 시작한다.
- **수정:** `_RecordsColumn` 에 `PageStorageKey` 를 받게 했다(1열 / 2열 왼쪽 /
  2열 오른쪽이 각각 다른 키 — 열의 내용이 달라서 위치를 섞으면 엉뚱한 곳이 열린다).
  `ScrollPosition` 이 스크롤이 끝날 때 라우트의 `PageStorageBucket` 에 offset 을
  쓰고, 다시 만들어질 때 그 값을 읽는다.
- **증명:** `mobile/test/screens/ranking_records_tablet_test.dart`
  "390 → 1024 → 390 왕복에도 읽던 스크롤 위치가 남는다".

```
# 재현(red) — 고치기 전 (리뷰의 실제 앱 184.0 → 0.0 과 같은 증상)
Expected: <126.0>
  Actual: <0.0>

# 고친 뒤(green)
00:01 +24: … SCREENS T4 내 기록 390 → 1024 → 390 왕복에도 읽던 스크롤 위치가 남는다
```

### D-27-4 (MINOR) — S3 로딩 스켈레톤이 짧은 가로 화면에서 overflow

- **원인:** 로딩 Column 이 고정 높이(머리글 + 8줄 × 46dp)를 그대로 쌓고 가용 높이를
  제한하지 않는다.
- **수정:** 목록 자리를 `Expanded` + `ListView.builder`
  (`NeverScrollableScrollPhysics`)로 바꿨다 — 로드가 끝난 `_Board` 와 같은 구조이고,
  남는 높이만 쓰고 넘는 줄은 그리지 않는다. 기다리는 동안의 자리 표시라 스크롤할
  것도 없다. 스피너는 그대로 쓰지 않는다(OVERRIDES §7).
- **증명:** `mobile/test/screens/ranking_tab_test.dart`
  "로딩 스켈레톤은 짧은 가로 화면(844x390)에서도 넘치지 않는다".

```
# 재현(red) — 고치기 전 (리뷰와 같은 106 pixels)
Expected: null
  Actual: FlutterError:<A RenderFlex overflowed by 106 pixels on the bottom.>

# 고친 뒤(green)
00:00 +19: … 로딩 스켈레톤은 짧은 가로 화면(844x390)에서도 넘치지 않는다
```

### 리뷰가 인정하지 않은 주장 — "늦은 응답을 버리는 테스트"

리뷰 "보안·범위·공유 파일" 절의 지적이 맞다. 이전 라운드의 컨트롤러 테스트 5개엔
쓰기 직렬화(게이트)만 있고 **다시 빌드 후 늦은 응답이 도착하는** 사례가 없었다.
`mobile/test/settings/puzzle_language_controller_test.dart` 에
"다시 빌드된 뒤 도착한 늦은 응답은 새 정본을 덮지 않는다" 를 추가했다 — 쓰기를
게이트로 붙잡은 채 provider 를 무효화하고(정본 재설정) 그 뒤 응답을 도착시켜,
`change()` 가 `false` 를 주고 언어가 새 정본(ko)으로 남는 것을 본다.

```
00:00 +4: test/settings/puzzle_language_controller_test.dart: 다시 빌드된 뒤 도착한 늦은 응답은 새 정본을 덮지 않는다
```

### 공유 파일

`README.md` 의 티켓 27 절 "알려진 제한" 을 고친 동작으로 갱신했다(결과 확정 시
무효화 경로 + 남은 제한은 "그 사이 올라온 다른 사람 순위" 와 자정 넘김). 그 밖의
공유 파일(`.env.example`·`docs/`·`.scratch/`·마이그레이션)은 바꾸지 않았다.

### 미수정 MINOR

없다. MINOR 2건(D-27-3·D-27-4) 모두 고쳤다.

### 재검증 (리베이스 후, 실제 실행 출력)

로컬 `main`(45d790c — 티켓 16 병합 포함) 위로 리베이스했다. 충돌 없음, `origin`
push 없음.

```
$ git rebase main
Successfully rebased and updated refs/heads/dosaem/t27-app-leaderboard-records-settings.

$ cd mobile && flutter test
00:40 +269: All tests passed!          # 259 → 269 (이번 라운드 +10)

$ cd mobile && flutter analyze
No issues found! (ran in 2.8s)

$ cd mobile && dart format --output=none --set-exit-if-changed lib test
Formatted 88 files (0 changed) in 0.12 seconds.    # exit 0

$ uv run ruff check .
All checks passed!

$ cd mobile && flutter build apk --debug            # 코디네이터 메모: JDK 가 고쳐졌다
Running Gradle task 'assembleDebug'...                             40.9s
✓ Built build/app/outputs/flutter-apk/app-debug.apk                # exit 0
# 빌드 뒤 mobile/build(2.4G) 삭제 — 작업 트리 clean
```

마이그레이션은 이번에도 0건이라(`git diff --name-only main...HEAD -- migrations`
출력 없음) `flask db heads` 는 해당 없음.
