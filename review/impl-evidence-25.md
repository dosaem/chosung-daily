# 티켓 25 구현 증거 — S1 오늘 (퍼즐 보드·제출·피드백·409 새로고침·상태 4종)

**브랜치:** `dosaem/t25-app-home-play-flow` · **날짜:** 2026-10-14
**범위:** Flutter 앱(`mobile/`)만. 백엔드·웹·마이그레이션은 건드리지 않았다.

## 0. 한 줄 요약

S1 오늘 탭을 서버 이력으로 그리는 보드 + 제출 + 글자별 피드백 + 409 새로고침 +
상태 6종(로딩·정상·오류·오프라인·퍼즐 없음·완료)으로 채웠고, SCREENS T1 의 태블릿
2열까지 넣었다. 앱 테스트 187개 통과(이 티켓이 더한 건 67개), 백엔드 800개 통과,
`flutter analyze`·`dart format`·`ruff` 무이슈, APK·iOS 디버그 빌드 성공.

## 1. 티켓 체크박스 ↔ 증거

| 체크박스 | 증명하는 테스트/명령 | 위치 |
|---|---|---|
| ApiClient 에 `GET /puzzles/today`, `POST /puzzles/today/guesses`, `PATCH /me` 추가(Dio + Fake) | `test/api/dio_api_client_test.dart` "퍼즐 엔드포인트" 6개(경로·메서드·Bearer·본문·409·404·토큰 없음), `test/api/api_models_test.dart` `TodayPuzzle.fromJson`·`GuessResult.fromJson` 5개 | §3.1 |
| `PuzzleBoard`·`GuessInput`·`HintCard`·`StreakBadge`·날짜 줄 + "KST 00:00 새 퍼즐" 칩 | `today_tab_test.dart` "정상: 날짜 줄·칩·보드·힌트·입력이 다 있다"(타일 24칸·칩·"4글자"·"남은 기회 5/5"), "힌트가 열리면 잠김 문구 대신 힌트가 보인다", 골든 3장 | §3.2·§5 |
| Riverpod 상태 6종 · 제출 `puzzle_id` 동봉 · 409 재조회 · en `s` 재삽입 | `today_puzzle_controller_test.dart` 12개, `today_tab_test.dart` "상태 4종" 6개 + "제출" 4개, `board_layout_test.dart` 7개 | §3.3 |
| 앱 시작·포그라운드 복귀 재조회 | `today_puzzle_controller_test.dart` "재조회" 2개, `today_tab_test.dart` "포그라운드 복귀 시 오늘 퍼즐을 다시 읽는다"(실제 생명주기 전이) | §3.3 |
| 위젯 테스트(Fake ApiClient): 상태 4종·제출→409→새로고침·완료 "결과 보기"·다크모드 | `today_tab_test.dart` 17개 + 골든 3장 | §3.4·§5 |
| 태블릿 T1(폭 390/744/1024 분기, 744→390 유지) | `today_tab_tablet_test.dart` 6개 | §3.5 |
| `audit.native` 통과 + 목업 대비 스크린샷 | §4 체크리스트, §5 골든 3장 | §4·§5 |

마이그레이션을 만들지 않았으므로 `flask db heads` 는 해당 없음(백엔드 파일 0개 변경).

## 2. 바뀐 파일

**새로 만든 것**

| 파일 | 역할 |
|---|---|
| `mobile/lib/puzzle/guess_rules.dart` | `normalizeGuess`(서버 `normalize_for_compare` 와 같은 규칙)·`applyGuess`·`timeUntilNextPuzzle`·`formatCountdown` — 전부 순수 함수 |
| `mobile/lib/puzzle/board_layout.dart` | `mask` 를 걸어가며 보드 한 행을 칸 목록으로 바꾸는 순수 함수(문제·시도·빈 행) + `tileSize` |
| `mobile/lib/puzzle/today_puzzle_state.dart` | `TodayPuzzleReady` / `TodayNoPuzzle` / `TodayNotice` |
| `mobile/lib/puzzle/today_puzzle_controller.dart` | `AsyncNotifier` — 조회·재시도·포그라운드 재조회·제출(409/오프라인 분기) |
| `mobile/lib/widgets/puzzle_board.dart` | `PuzzleBoard`·`BoardTile`·`BoardGap` |
| `mobile/lib/widgets/guess_input.dart` | `GuessInput`(카운터·제출)·`AttemptsLeftLabel` |
| `mobile/lib/widgets/hint_card.dart` | `HintCard` 잠김/열림 |
| `mobile/lib/widgets/offline_banner.dart` | `OfflineBanner` |
| `mobile/test/puzzle/*`(3), `mobile/test/screens/*`(2), `mobile/test/golden/*`(테스트 1 + PNG 3) | 테스트·골든 |

**고친 것**

| 파일 | 변경 |
|---|---|
| `mobile/lib/api/api_client.dart`·`dio_api_client.dart`·`api_models.dart`·`api_exception.dart` | 엔드포인트 3개, 모델 5종(`MaskTile`·`PuzzleAttempt`·`TodayPuzzle`·`GuessResult`·`WordCategory`/`PuzzleStatus`), 예외 2종(`NO_PUZZLE_TODAY`·`PUZZLE_CHANGED`) |
| `mobile/lib/screens/today_tab.dart` | 뼈대 → S1 전체 + T1 2열 |
| `mobile/lib/theme/app_theme.dart` | 주 버튼 `textStyle` 에 글꼴 지정(§4 결함 2) |
| `mobile/assets/translations/{ko,en}.json` | `today.*`·`hint.*`·`category.*` 추가(키 집합 동일) |
| `mobile/test/fakes/fake_api_client.dart` | 새 메서드 3개 + `fakeTodayPuzzle`·`fakeGuessResult` + 응답 지연 게이트 |
| `README.md` | "설계 판단" 에 `### 25.` 추가. API 표는 이미 세 엔드포인트가 있어 변경 없음 |

`.scratch/` 의 스펙·티켓·디자인 파일은 고치지 않았다. 스펙 "미정 항목" 13(en 구분자
재삽입)은 **이 티켓이 그 규칙대로 구현**했고 근거를 README "25." 에 적었다 — 확정
문구를 스펙에 적는 건 미정 13 을 맡은 티켓 17(웹)의 자리라 건드리지 않았다.

## 3. 테스트 (red → green 으로 쓴 순서)

### 3.1 API 경계

`test/api/dio_api_client_test.dart` 는 네트워크를 타지 않는 가짜 `HttpClientAdapter`
로 **보낸 요청**을 본다: `/puzzles/today` 가 Bearer 를 달고 GET 인지, 제출 본문이
`{puzzle_id, guess}` 인지, 404 `NO_PUZZLE_TODAY`·409 `PUZZLE_CHANGED` 가 전용
예외가 되는지, 토큰이 없으면 서버까지 가지 않는지. `PATCH /me` 도 같은 방식이다.

### 3.2 순수 함수

- `guess_rules_test.dart`(11): 구분자 제거·en 대문자, 제출 응답을 보드에 반영
  (오답·정답·마지막 기회·en 정규화·힌트 유지), KST 자정까지 남은 시간(기기
  시간대 무관), 카운트다운 포맷.
- `board_layout_test.dart`(7): 문제 행/시도 행/빈 행, **en 의 `s` 간격 재삽입**,
  글자가 모자란 옛 행, 타일 크기 48/40.

### 3.3 상태

`today_puzzle_controller_test.dart`(12): 시작 조회 1회, 퍼즐 없음, 네트워크 오류,
재시도, 제출이 `puzzle_id` 를 동봉하고 보드에 한 행을 쌓는 것, 글자 수가 안 맞으면
서버에 안 가는 것, **409 → 재조회 + 메시지(시도 미소비)**, 오프라인/그 밖 오류에
보드를 지우지 않는 것, 끝난 퍼즐 재제출 차단, 포그라운드 재조회가 스켈레톤으로
돌아가지 않는 것.

### 3.4 화면(Fake ApiClient, 실제 위젯 트리)

`today_tab_test.dart`(17): 로딩 스켈레톤 → 보드, 정상 화면 구성, 오류 카드 + 재시도,
오프라인 배너, 퍼즐 없음 카운트다운, 완료 "결과 보기", 글자 수에 따른 제출 버튼
활성, 제출 후 입력창 비움, **제출 → 409 → 새 보드 + "새 퍼즐이 있어요"**, 제출
오프라인 시 입력 잠금, 피드백이 색 외에 아이콘·취소선으로도 구분되는 것, en 보드
간격, 다크 토큰으로 그려지는 것, 포그라운드 복귀, 글자 1.3배, 입력 칸이 카운터에
밀리지 않는 것.

### 3.5 태블릿

`today_tab_tablet_test.dart`(6): 390 1열 · 744 rail+1열(읽기 폭 600 가운데) ·
1024 2열(힌트·남은 기회가 오른쪽 열 ≤320, 두 열 합 ≤920) · 타일 크기 폰과 동일 ·
**744→390 폭 변경 후 입력 텍스트·보드 유지(재조회 0회)** · 1024→744(2열→1열)에서도
입력 텍스트 유지.

## 4. `audit.native` 체크리스트 (impeccable `reference/audit.native.md`)

브라우저 도구·`impeccable detect` 는 쓰지 않는다(HTML/CSS 용). 22·24 와 같이 소스를
`reference/ios.md`·`android.md` 기준으로 읽고 5축에 점수를 매겼다. 폭 확인은 눈이
아니라 위젯 테스트(390·744·834·1024·1366)와 골든 3장이다.

| # | 축 | 24 | 25 | 핵심 소견 |
|---|---|---|---|---|
| 1 | Accessibility | 3 | **4** | 타일마다 "글자 + 맞음/아님" 레이블(색만으로 구분하지 않는다, US 3), 시도 행에 "시도 N" 컨테이너, `StreakBadge` 가 "연속 기록 7일" 로 읽힌다(24 가 남긴 P3 해소), 스켈레톤은 `ExcludeSemantics`(24 의 P3 해소). 터치 타깃은 제출·힌트 버튼·입력이 48 이상(테마 `_minTouchTarget`). 타일은 누르는 요소가 아니라 해당 없음. 글자 1.3배 테스트 통과 |
| 2 | Performance | 3 | 3 | 보드는 최대 6행 × 8칸이라 가상화가 필요 없다. 제출이 왕복 1회(응답으로 한 행 반영). 재조회는 스켈레톤으로 되돌리지 않아 트리를 다시 세우지 않는다 |
| 3 | Appearance & Theming | 4 | 4 | 새 위젯 전부 `AppColors` 토큰만 쓴다. raw hex 는 여전히 `app_colors.dart` 한 파일뿐. 라이트·다크 골든 2장으로 두 모드를 같이 본다 |
| 4 | Platform Conformance | 3 | 3 | Material 기본 컨트롤(`TextField`·`FilledButton`·`OutlinedButton`), 시스템 back·edge-swipe 를 건드리지 않는다. 한글 IME 는 `maxLength` 기본 enforcement(조합 중 자르지 않음)로 끊기지 않는다. 아이콘 Lucide 는 OVERRIDES §8 의 의도된 이탈(22 부터) |
| 5 | Adaptivity | 3 | **4** | T1 2열/1열 분기 + 폭 왕복 상태 유지 + 키보드는 열마다 `SingleChildScrollView` 가 받는다. 타일 확대 금지 확인 |
| **합계** | | **16/20** | **18/20** | **Excellent (minor polish)** |

**추가 항목 "태블릿 폭(744·1024·1366) 포함": 통과.** 744·1024 는 T1 레이아웃
테스트가, 1366 과 834·390·320 은 24 의 셸 테스트가 그대로 덮는다(이 티켓은 셸
안에서 돌아간다 — 태블릿 테스트가 `AdaptiveScaffold` 를 실제로 끼운다).

### 이 티켓이 고친 실제 결함 2건 (골든이 잡았다)

1. **입력 칸이 0폭이었다.** 글자수 카운터를 `suffixIcon` 안에서 `Align` 으로
   감쌌더니 남은 폭을 전부 먹어, 안내 문구도 치는 글자도 보이지 않았다(골든에
   "정답을 입력하세요" 가 통째로 없었다). `Align` → `Center(widthFactor: 1)` 로
   바꿨고 `입력 칸과 안내 문구가 카운터에 밀려 사라지지 않는다` 테스트가 지킨다.
   위젯 테스트만으로는 못 잡았다 — 글자가 트리에 있기는 했다.
2. **주 버튼 글자만 시스템 글꼴이었다.** `ButtonStyle.textStyle` 은
   `ThemeData.fontFamily` 를 거치지 않아서 `filledButtonTheme` 의 `TextStyle` 에
   글꼴이 없으면 Pretendard 가 아니다(OVERRIDES §3 위반). `app_theme.dart` 에
   글꼴·폴백을 명시했다. P2, 골든 비교로 확인.

### 의도된 이탈 / 남은 결함

| 심각도 | 위치 | 내용 | 받는 곳 |
|---|---|---|---|
| P2 | `_ShowResultButton` | 완료 상태의 "결과 보기" 가 **눌리지 않는다**(`onPressed: null`) — 결과 시트는 티켓 26 이다. 버튼 자리·문구·상태만 확정했다 | 티켓 26 |
| P2 | `HintCard` | "광고 보고 힌트 미리 보기" 버튼도 같은 이유로 비활성(보상형 광고·`hint-unlock` 호출은 31) | 티켓 31 |
| P3 | `PuzzleBoard` | OVERRIDES §7 의 타일 뒤집기 모션(350ms, 행 stagger 60ms)을 넣지 않았다. `prefers-reduced-motion` 분기도 그때 같이 | 티켓 26 이후 폴리시 |
| P3 | 제출 실패 문구 | 429 `RATE_LIMITED` 를 따로 구분하지 않고 "제출하지 못했어요" 로 묶는다 — 서버 메시지를 그대로 쓰면 en 사용자에게 한국어가 나간다 | — (의도) |
| P2 | — | 시뮬레이터·실기기 스크린샷은 없다. 골든은 테스트 렌더러다 | 티켓 35·36 |

### 디자인 파일과 다르게 구현한 곳

1. **`tile-wrong` 타일에 취소선.** 목업(`e1_home`·`e7_home_dark`)은 틀린 칸을 색만
   다르게 두지만 OVERRIDES §2 가 "correct 는 체크 아이콘, wrong 은 취소선/흐림" 을
   요구한다. 충돌 시 OVERRIDES 우선이라 취소선을 넣었다.
2. **HintCard 에 면을 깔지 않는다.** `e7_home_dark` 는 카드 면(`#1C2433`)을 쓰지만
   OVERRIDES §4 는 "라이트에선 카드 없음, 바텀시트만 `card` 면" 이다. 두 모드가
   어긋나지 않게 헤어라인 테두리만 쓴다.
3. **제출 버튼이 입력 아래 전폭.** `e1_home` 은 "남은 기회" 와 한 줄에 놓지만
   SCREENS S1 본문과 T1 와이어가 "입력 → 제출 → 남은 기회" 순서라 그쪽을 따랐다.
4. **문제 행 캡션("4글자")이 타일 아래.** `e1_home` 은 위, `e7_home_dark` 는 아래다.
   둘이 다를 땐 다크 목업과 T1 와이어를 따랐다.

## 5. 목업 대비 스크린샷 기록

골든 3장(`mobile/test/golden/`, 생성·갱신은 `flutter test test/golden
--update-goldens`). Pretendard·Lucide 를 실제로 불러와 찍는다.

| 골든 | 대조 대상 | 결과 |
|---|---|---|
| `today_light_390.png` | `design/stitch/e1_home.html` | 상단 줄·날짜 줄·칩·타일 4칸·시도 2행(체크 아이콘)·빈 행 3줄·HintCard·입력+카운터·제출·남은 기회까지 같은 순서. 다른 점은 위 "디자인 파일과 다르게" 1·2·3 |
| `today_dark_390.png` | `design/stitch/e7_home_dark.html` | 다크 토큰(배경 `#141A26`, 타일 `#253044`, correct `#22C55E` + 어두운 글자)으로 같은 화면. HintCard 면 없음(위 2) |
| `today_tablet_1024.png` | SCREENS T1 와이어(expanded) | rail + 왼쪽 열(상단 줄·날짜 줄·보드·입력·제출) + 오른쪽 열(HintCard·"남은 기회"), 타일 크기 폰과 동일 |

## 6. 검증 (실제 실행 명령과 출력)

```
$ cd mobile && dart format --set-exit-if-changed .
Formatted 69 files (0 changed) in 0.15 seconds.        # exit 0

$ flutter analyze
Analyzing mobile...
No issues found! (ran in 4.0s)

$ flutter test
00:16 +187: All tests passed!                          # 24 머지 시점 120 → 187

$ JAVA_HOME=/opt/homebrew/opt/openjdk@17 flutter build apk --debug
Running Gradle task 'assembleDebug'...                             56.1s
✓ Built build/app/outputs/flutter-apk/app-debug.apk

$ flutter build ios --no-codesign --debug
Running Xcode build...
Xcode build done.                                           69.8s
✓ Built build/ios/iphoneos/Runner.app
```

빌드 뒤 `mobile/build`(2.9G)·`mobile/ios/Pods`(68M)를 지웠고, `pod install` 이
건드린 `ios/Runner.xcodeproj/project.pbxproj`·`contents.xcworkspacedata`·
`Podfile.lock` 은 되돌렸다(이 티켓의 변경이 아니다).

위 네 명령은 **로컬 `main`(티켓 14 머지, `7df7809`) 위로 rebase 한 뒤** 다시 돌린
결과다(rebase 충돌 없음). 백엔드는 코드를 안 건드렸지만 rebase 로 base 가 바뀌어
한 번 더 돌렸다(전용 자원: DB `chosung_daily_test_t25`, Redis 13, 마이그레이션 DB
`chosung_daily_test_t25_migrations`).

```
$ uv run ruff check .
All checks passed!

$ TEST_DATABASE_URL=...chosung_daily_test_t25 TEST_REDIS_URL=redis://127.0.0.1:6379/13 \
  TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t25_migrations uv run pytest -q
800 passed in 623.10s (0:10:23)
```

## 7. 숨기지 않는 것

- **실기기·시뮬레이터에서 띄우지 않았다.** 골든은 Flutter 테스트 렌더러가 그린
  그림이라 실제 기기의 글꼴 힌팅·safe area·IME 동작과 1:1 은 아니다. 한글 IME 조합
  중 동작은 `maxLength` 기본 enforcement 에 기대고 있고 실기기 확인은 티켓 35·36 의
  사람 체크리스트가 받는다.
- **골든은 이 기계(macOS, Flutter 3.38.6)에서 만든 파일이다.** 렌더러가 바뀌면
  차이가 날 수 있고, 그때는 `--update-goldens` 로 다시 찍고 사람이 본다.
- **보상형 힌트·결과 시트·전면 광고가 없다**(티켓 26·31). 완료 상태에서 정답을
  보여주는 경로가 26 머지 전까지는 없다.
- **`PATCH /me` 는 앱 코드에서 아직 아무도 부르지 않는다.** 티켓이 지정한 항목이라
  ApiClient·Fake·Dio 테스트까지만 넣었고, 쓰는 쪽은 설정 화면(29·30)이다.
