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
| ~~P3~~ | `PuzzleBoard` | ~~OVERRIDES §7 의 타일 뒤집기 모션(350ms, 행 stagger 60ms)을 넣지 않았다~~ → **수정 라운드 1 에서 넣었다**(D-25-4, 아래 §8) | 해소 |
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

---

## 8. 수정 라운드 1 (리뷰 `review/impl-review-25.md` 라운드 1)

Codex 최종 리뷰 r1 의 판정은 FAIL — MAJOR 3건(D-25-1·2·3), MINOR 1건(D-25-4).
**네 건 모두 고쳤고**, 각 결함은 리뷰에 적힌 재현 순서를 그대로 테스트로 세워
먼저 빨갛게 만든 뒤 고쳤다(red → green). 리뷰어 지적이 틀렸다고 판단한 건
없다. 아래 "덧붙이는 판단" 두 줄만 고치지 않은 이유를 적었다.

구현 커밋: `fix(25): 리뷰 r1 — 응답 경합·오류 복구·타일 뒤집기 모션`.
앱 테스트 **187 → 202**(이 라운드가 더한 건 15개: 컨트롤러 10, 화면 5).
세대 장치를 표로 정리하면서(아래 "경합 표") 리뷰에 없던 경합 1건(#7)을 더 찾아
같이 고쳤다.

### D-25-1 — 늦은 조회/제출 응답이 최신 보드와 제출 잠금을 덮어쓴다 (MAJOR)

**원인.** 조회·제출·409 재조회 세 경로가 모두 "응답이 오면 무조건 쓴다" 였다.
요청 세대도, 서로의 순서 보장도 없어서 (a) 제출이 시작할 때 캡처한 `puzzle` 에
`applyGuess` 를 적용해 그 사이 읽어온 새 보드를 과거로 되돌리고, (b) 제출 전에
떠난 `GET` 이 늦게 도착하면 방금 쌓은 행을 지우고, (c) 제출 대기 중 `_load()` 가
`submitting: false` 인 상태를 만들어 중복 제출을 다시 열었다.

**수정** (`lib/puzzle/today_puzzle_controller.dart`).

1. **세대 번호**(`_generation`): 조회·제출·다시 빌드가 떠날 때 번호를 올리고,
   응답이 돌아오면 자기 번호가 아직 최신일 때만 상태에 쓴다(`_canCommit`). 먼저
   떠난 느린 응답은 버린다. `retry()`(`invalidateSelf`)도 세대를 올리는 사건이다
   — Riverpod 은 notifier 객체를 그대로 두고 `build` 만 다시 부르므로 "버려졌다"
   에 기대면 안 된다(경합 표 #7). provider 자체가 버려진 경우는 `ref.mounted` 가
   받는다.
2. **제출은 보드를 독점한다**: 제출 응답을 기다리는 동안의 `refresh()` 는 보드를
   건드리지 않고 `_refreshQueued` 로 미뤘다가 제출이 끝난 뒤 한 번 돌린다. 그래서
   (a) 는 "제출 결과 → 그다음 서버 보드" 순서가 되고(최종 상태는 리뷰가 기대한
   새 퍼즐 B), (c) 의 잠금은 풀리지 않는다. 제출 중 읽은 이력엔 방금 보낸 답이
   아직 없다는 게 핵심이다 — 그걸 쓰면 사용자가 본 행이 사라진다.
3. **첫 조회 중의 복귀는 그 조회를 기다린다**: `build()` 가 돌려준 future 는
   프레임워크가 직접 상태에 쓰므로 세대 검사로 버릴 수 없다. 그래서 두 번째
   조회를 아예 띄우지 않는다(`state.isLoading && !state.hasValue` → 즉시 반환).

**증명.** `test/puzzle/today_puzzle_controller_test.dart` group `응답 경합` 4개.
`FakeApiClient` 에 `submitGuessGate` 를 더하고, 응답 값을 **호출 시점에** 붙잡게
고쳐(`final response = puzzle;`) "늦게 도착한 옛 응답" 을 테스트가 만들 수 있게
했다 — 고치기 전에는 붙잡아 둔 조회가 그 사이 바뀐 값을 돌려줘서 경합 자체를
재현할 수 없었다.

| 테스트 | 고치기 전 |
|---|---|
| 제출을 기다리는 동안엔 재조회가 보드를 건드리지 않는다 — 잠금도 유지된다 | `Expected: <41> Actual: <42>` (제출 중 보드가 바뀌고 잠금이 풀렸다) |
| 제출 전에 떠난 조회가 늦게 도착해도 쌓인 행을 지우지 않는다 | `Expected: an object with length of <1> Actual: []` |
| 느린 재조회 뒤에 떠난 재조회가 이긴다 | 늦게 온 옛 응답(`attemptsLeft 4`)이 최신(`3`)을 덮었다 |
| 첫 조회가 끝나기 전의 복귀는 그 조회를 기다린다 — 두 번 읽지 않는다 | (새 보호 장치) |

### D-25-2 — 보드가 있는 상태의 네트워크 실패에 재시도 경로가 없다 (MAJOR)

**원인.** 두 갈래였다.

- 제출이 `NetworkApiException` 으로 실패하면 `TodayNotice.offline` 이 **영구히**
  남는다. 보드 화면엔 오류 카드가 없어 재시도를 띄울 자리가 없었고, 그래서
  연결이 돌아와도 앱을 내렸다 올리는 것 말고는 입력을 열 방법이 없었다.
- 재조회 실패를 `AsyncError` 로만 남겼다. Riverpod 3.3.2 의 `copyWithPrevious`
  가 이전 값을 함께 들고 있어서 화면의 `switch` 는 앞의 `Ready` 분기를 고르고,
  오류는 아무도 안 보는 곳에 남는다 — 실패한 적이 없는 화면처럼 보였다. 409 뒤
  재조회가 실패하면 그 "이전 값" 이 `submitting: true` 라 입력이 영구히 잠겼다.

**수정.**

1. `_commitLoad` 가 조회 실패를 **상태로** 바꾼다: 보드가 있으면 보드를 지우지
   않고 `TodayNotice.offline`(네트워크) / 새 `TodayNotice.refreshFailed`(그 밖)
   를 올린다(`submitting` 은 자연히 풀린다). 보드가 없을 때만 `AsyncError` 로
   둬서 오류 카드가 받는다. 409 재조회 실패도 같은 경로를 탄다.
2. `TodayNotice.showsRetry`(= `offline`·`refreshFailed`) 를 더하고, 화면에
   인라인 재시도를 붙였다: 오프라인은 상단 `OfflineBanner(onRetry:)` 안에,
   `refreshFailed` 는 보드 위 안내 줄 끝에. 재시도는 `refresh()` 라서
   스켈레톤으로 돌아가지 않는다(멀쩡한 보드를 깜빡이게 하지 않는다).
   오프라인일 때 안내 줄을 생략하게 바꿨다 — 배너가 이미 같은 문장을 말한다.

**증명.**

| 테스트 | 고치기 전 |
|---|---|
| (화면) 제출이 오프라인으로 실패해도 배너의 재시도로 입력이 다시 열린다 | 재시도 버튼이 없어 `findsOne` 실패 |
| (화면) 재조회가 서버 오류로 실패하면 보드 위에 안내 + 재시도가 남는다 | 안내·재시도 둘 다 없음(화면이 정상처럼 보인다) |
| (컨트롤러) 서버 오류면 보드를 남기고 "다시 불러오지 못했어요" 안내를 올린다 | `hasError` `Expected: false Actual: <true>` |
| (컨트롤러) 네트워크 오류면 오프라인 안내로 바꿔 입력을 잠근다 | `notice` 가 `null` |
| (컨트롤러) 409 뒤 재조회가 실패해도 제출 잠금이 풀린다 | `submitting` `Expected: false Actual: <true>` |
| (컨트롤러) 제출이 오프라인으로 실패한 뒤 재시도로 입력이 다시 열린다 | (복구 경로 고정) |

### D-25-3 — 이전 안내 메시지가 있으면 재조회 오프라인 오류를 무시한다 (MAJOR)

**원인.** `today_tab.dart` 의 `ready.notice?.blocksInput ?? _isOffline(state.error)`
는 **notice 가 있으면 오른쪽을 아예 평가하지 않는다**(`??` 는 null 일 때만 본다).
그래서 `puzzleChanged`·`submitFailed` 가 떠 있는 동안의 네트워크 오류는 배너도
입력 잠금도 만들지 못했다. 판정이 두 곳(notice / `state.error`)에 흩어져 있던 게
뿌리다.

**수정.** 판정을 notice 하나로 모았다 — D-25-2 의 `_commitLoad` 가 재조회 실패를
항상 notice 로 바꿔 놓으므로 보드 분기는 notice 만 보면 된다. 남은
`state.error` 는 `??` 가 아니라 `||` 로 **같이** 본다(두 번째 방어선). 덧붙여
오류 분기를 "퍼즐 없음" 앞으로 옮겼다 — 카운트다운 카드에서 재시도가 실패하면
같은 `copyWithPrevious` 때문에 실패가 안 보였다.

**증명.** `(컨트롤러) 앞선 안내가 있어도 재조회 오프라인이 안내를 덮어쓴다`
— 고치기 전 `Expected: offline Actual: puzzleChanged`. 화면 쪽은
`앞선 안내가 있어도 재조회가 오프라인이면 배너가 뜨고 입력이 잠긴다`(409 →
"새 퍼즐이 있어요" → 복귀 `GET` 네트워크 실패 → 배너 + `TextField.enabled false`
+ 제출 버튼 `onPressed null`)로 고정했다.

### D-25-4 — 명시된 타일 피드백 전환 모션이 없다 (MINOR)

**원인.** `PuzzleBoard` 가 전부 `StatelessWidget` 이라 애니메이션을 걸 자리가
없었다. 구현 증거 §4 가 이걸 후속 폴리시로 넘겼지만 티켓이 참조하는 OVERRIDES
§7 에는 그런 유예가 없다 — 리뷰 판단이 맞다.

**수정.** 시도 행이 **처음 그려질 때** 뒤집히며 들어온다(`_FlipIn`):
`rotateX` 90° → 0°, 350ms `easeOut`, 행마다 60ms 늦게 시작. stagger 는 기다리는
구간을 커브 앞(`Interval`)에 끼워 만들었다 — `Timer` 를 따로 두면 위젯이 먼저
사라졌을 때 취소할 자리를 하나 더 챙겨야 한다. 상태가 아니라 "행이 새로 붙었다"
(element 가 새로 생겼다)에 매달려 있어서 보드가 다시 그려져도 이미 있던 행은
다시 뒤집지 않는다. `MediaQuery.disableAnimationsOf`(iOS "동작 줄이기" ·
Android 애니메이션 제거)면 즉시 표시한다. 다 열린 행은 변환 자체를 걷어내
끝난 뒤까지 3D 레이어를 남기지 않는다 — **골든 3장은 그래서 1픽셀도 안 바뀌었다**
(`flutter test test/golden` 통과, `--update-goldens` 없이).

**증명.** `test/screens/today_tab_test.dart` group `타일 피드백 모션` 2개:
`제출한 행은 뒤집히며 들어오고 끝나면 변환이 걷힌다`(고치기 전
`Found 0 widgets with type "Transform"`), `모션 감소 설정이면 뒤집지 않고 바로
보여준다`(변환 없음 + `hasRunningAnimations` false).

### 상태를 바꾸는 사건 × 경합 표

코디네이터 메모대로 개별 응답에 조건을 덧대지 않고 **원인 구조**로 막았다. 상태를
바꾸는 사건(첫 조회·다시 빌드(`retry()`)·포그라운드 복귀/알림 탭·인라인 재시도·
제출 시작·409 재조회)은 떠날 때 세대를 올리고, 모든 비동기 응답은 **상태 반영 직전 한 곳**(`_canCommit`,
`_commitLoad`/`_commitNotice`/제출 성공이 모두 이걸 통과한다)에서 세대를 비교해
다르면 버린다. 서버 쓰기(제출)는 직렬화한다 — 제출 중엔 다른 제출도(기존
`submitting` 잠금) 재조회도 보드를 건드리지 못한다.

가짜 시계는 쓰지 않았다. 여기서 중요한 건 "시간" 이 아니라 **응답 도착 순서**라서
`FakeApiClient` 의 지연 게이트(`submitGuessGate`·`fetchTodayPuzzleGate`)로 순서를
직접 만들었다. 모션(D-25-4)만 테스트 바인딩의 시계(`tester.pump(Duration)`)를 쓴다.

| # | 겹치는 두 사건(먼저 떠난 쪽 → 나중) | 고치기 전 결과 | 막는 장치 | 고정한 테스트 |
|---|---|---|---|---|
| 1 | 제출 → 복귀 재조회 (제출 응답 전) | 늦은 `POST` 응답이 새 보드를 되돌린다 | 제출이 보드를 독점, 재조회는 제출 뒤로 미룸 | 제출을 기다리는 동안엔 재조회가 보드를 건드리지 않는다 |
| 2 | 제출 → 복귀 재조회 (같은 퍼즐) | `_load()` 가 `submitting: false` 를 만들어 중복 제출 허용 | 같음(미룸) + 기존 `submitting` 잠금 | 같은 테스트의 `submitting isTrue` |
| 3 | 복귀 재조회 → 제출 (조회 응답 전) | 늦은 `GET` 의 옛 이력이 쌓인 행을 지운다 | 세대 비교 | 제출 전에 떠난 조회가 늦게 도착해도 쌓인 행을 지우지 않는다 |
| 4 | 재조회 → 재조회 (복귀 연속·재시도 연타) | 늦게 온 옛 응답이 이긴다 | 세대 비교 | 느린 재조회 뒤에 떠난 재조회가 이긴다 |
| 5 | 첫 조회(`build`) → 복귀 재조회 | `build` 의 future 가 나중에 상태를 덮어쓴다(프레임워크가 직접 쓰므로 세대로 못 버린다) | 첫 조회가 끝나기 전엔 두 번째 조회를 아예 띄우지 않는다 | 첫 조회가 끝나기 전의 복귀는 그 조회를 기다린다 |
| 6 | 409 재조회 → 실패 | `submitting: true` 가 영구히 남아 입력이 잠긴다 | `_commitLoad` 가 보드 + 안내로 되돌린다 | 409 뒤 재조회가 실패해도 제출 잠금이 풀린다 |
| 7 | 재시도(`invalidateSelf`) → 이전 빌드에서 떠난 응답 | 늦은 응답이 **새로 세운 보드에 그대로 쓰인다**(Riverpod 은 notifier 객체를 그대로 두고 `build` 만 다시 부른다 — 이 표를 테스트로 옮기다가 찾았다) | `build()` 도 세대를 올린다 + `_canCommit` 의 `ref.mounted` | 재시도로 provider 가 다시 세워지면 이전 세대의 응답은 조용히 버린다 |
| 8 | 언어 전환 `PATCH /me` → 보드 조회 | (앱에 호출자가 없다 — 설정 화면은 티켓 29·30) | 이 티켓 범위 아님 | — (아래 "덧붙이는 판단") |

8번은 리뷰도 "아직 호출자가 없는 PATCH 언어 변경의 순서 문제는 이 티켓 결함으로
추정하여 추가하지 않았다" 고 적었다. 언어 전환을 붙이는 티켓은 **같은 세대 번호를
올리는 사건으로** 넣으면 된다(`refresh()` 를 호출하는 지점이 곧 그 자리다) —
받는 쪽이 보도록 README "설계 판단 25." 가 아니라 여기 적어 둔다.

### 덧붙이는 판단 (고치지 않은 것)

- **연결 변경 구독은 넣지 않았다.** D-25-2 가 "연결 변경 구독도 없어" 를 함께
  적었지만, 티켓·US 8·OVERRIDES §7 이 요구하는 건 "네트워크 오류엔 인라인
  재시도" 이고 그걸 넣었다. `connectivity_plus` 를 새로 들이는 건 의존성 추가라
  결함 수정 범위를 넘고(스펙에 없는 SDK), 실제로 연결 복구를 알아도 할 일은
  같은 `refresh()` 다. 자동 복구가 필요하다고 판단되면 별도 티켓이 맞다.
- **미수정 MINOR 없음.** 라운드 1 의 MINOR 는 D-25-4 하나였고 고쳤다.
- 리뷰가 결함으로 세지 않은 비활성 버튼 2개(결과 시트 26, 보상형 힌트 31)와
  실기기 스크린샷(35·36)은 그대로다 — §4 표의 판단을 유지한다.

### 재검증 (로컬 `main` 위로 rebase 후 전체 재실행)

로컬 `main` 은 그 사이 티켓 23 까지 머지돼 `82e59ea` 다. 그 위로 rebase 했고
(충돌 없음, 작업 트리 clean), 네 명령을 다시 돌렸다. `origin/main` 은 쓰지 않았다.

```
$ cd mobile && flutter analyze
No issues found! (ran in 3.2s)

$ cd mobile && dart format --output=none --set-exit-if-changed .
Formatted 69 files (0 changed) in 0.21 seconds.      # exit 0

$ cd mobile && flutter test
00:31 +202: All tests passed!                        # 골든 3장 포함, 187 → 202

$ cd mobile && JAVA_HOME=/opt/homebrew/opt/openjdk@17 flutter build apk --debug
Running Gradle task 'assembleDebug'...                             40.1s
✓ Built build/app/outputs/flutter-apk/app-debug.apk   # exit 0 — 뒤에 build(2.4G)·android/.kotlin 삭제

$ uv run ruff check .
All checks passed!                                   # exit 0

$ TEST_DATABASE_URL=...chosung_daily_test_t25 TEST_REDIS_URL=redis://127.0.0.1:6379/13 \
  TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t25_migrations uv run pytest -q
996 passed in 785.37s (0:13:05)                      # exit 0
```

백엔드 코드는 한 줄도 안 건드렸지만 rebase 로 base 가 바뀌어(티켓 23 머지로
800 → 996개) 한 번 더 돌렸다. 전용 자원만 썼다 — DB `chosung_daily_test_t25`,
마이그레이션 DB `chosung_daily_test_t25_migrations`, Redis DB 13. 공용
`chosung_daily_test`·Redis DB 1 은 건드리지 않았고 새 DB 를 만들지도, 기본 DB
폴백을 쓰지도 않았다. 접속 문자열의 인증 부분은 기록하지 않는다.

마이그레이션 파일을 만들지 않았으므로 `flask db heads` 는 이 라운드에서도 해당
없음(백엔드 소스 0개 변경).
