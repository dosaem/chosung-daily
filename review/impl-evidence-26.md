# 티켓 26 구현 증거 — S2 결과 시트 · 분포 · 공유 · 분석 이벤트

작성: 2026-10-14, Implementer(Claude Opus 5). 브랜치
`dosaem/t26-app-result-sheet-share-analytics`, 로컬 `main`(`24c584d`) 위로 rebase 완료.

검증은 전부 이 기계에서 **실제로 돌린 결과**다. 돌리지 않은 것·못 한 것은 §7 에 적었다.

## 1. 체크박스 ↔ 증거

| 티켓 체크박스 | 이걸 증명하는 테스트·명령 | 본문 |
|---|---|---|
| ApiClient 에 `GET /puzzles/today/stats` 추가(Dio + Fake) | `dio_api_client_test.dart` "GET /puzzles/today/stats 는 Bearer 를 달고 분포를 돌려준다"·"아직 퍼즐이 없으면 stats 도 전용 예외로 온다", `api_models_test.dart` `TodayStats.fromJson` 3개, `fake_api_client.dart` `fetchTodayStats`(호출 수·게이트·오류 주입) | §3.1 |
| S2 바텀시트: 결과 헤더(성공/실패) | `result_sheet_test.dart` "성공: 정답과 몇 번째 시도였는지 보여준다"·"실패: 아쉬움 문구와 정답을 보여준다"·"정답이 안 왔으면…"·"en 기기는 영어 문구다" | §3.4 |
| 〃 분포 막대 + 내 위치 | 〃 "시도 1~5 비율과 내 행 강조(US 9)"·"막대 길이가 비율에 비례한다"·"실패한 사람은 분포에 내 행이 없다"·"조회 중엔 스켈레톤"·"실패하면 시트 안에서 다시 시도한다"·"아직 아무도 못 풀었으면 막대 대신 한 줄" | §3.4 |
| 〃 KST 카운트다운 | `puzzle_countdown_test.dart` 3개(가짜 시계로 KST 환산·1초 틱·타이머 해제), `result_sheet_test.dart` "다음 퍼즐까지 남은 시간을 보여준다(US 6)" | §3.3 |
| 〃 공유 버튼(`share_plus`, `…?utm_source=share`) | `share_text_test.dart` 6개, `result_sheet_test.dart` "공유 텍스트는 웹과 같은 포맷 + 링크다(US 10·11)"·"실패한 결과도 공유한다" | §3.2·§3.4 |
| 〃 "기록을 지키려면 연결하세요" 1회 안내 자리 | `result_sheet_test.dart` "자리가 있고 닫으면 사라진다" | §3.4 |
| Analytics 인터페이스 + Firebase 구현 + no-op 구현, 이벤트 4개 확정 | `analytics_event_test.dart` 4개(이름·파라미터 표 고정, `success` 1/0, 값은 String·num 뿐), `analytics_service_test.dart` 5개(no-op 기록, Firebase 가 이름·파라미터를 그대로 넘김, provider 가 Firebase 부팅 결과로 구현을 고름) | §3.5 |
| 스펙 미정 20 에 확정 결과 기록 | `.scratch/store-launch/spec.md` "미정 항목" 끝에 `- (티켓 26 반영) 미정 20 확정: …` | §2 |
| 위젯 테스트: 결과 시트 렌더(성공/실패)·공유 텍스트 구성·`puzzle_complete`·`share` 호출 | `result_sheet_test.dart` 18개 + `today_tab_test.dart` "결과 시트(S2)" 4개(제출로 끝남→시트+이벤트, 실패 경로 `success` 0·`attempts` 5, 안 끝난 제출은 둘 다 없음, 이미 끝난 퍼즐은 자동으로 안 뜸) | §3.4·§3.6 |
| 태블릿(T2): `showAdaptiveSheet`, compact 바텀시트 / medium+ 다이얼로그(≤560) | `result_sheet_tablet_test.dart` 6개(390 바텀시트 · 744 다이얼로그 폭·여백·가운데 · 744 내용 전부 · 744 공유·순위 동작 동일 · 손잡이는 바텀시트만 · 1024 도 다이얼로그) | §3.7 |
| `audit.native`(태블릿 폭 포함) 통과, 목업 `e2_result` 대비 기록 | §4 체크리스트 + §5 골든 3장 | §4·§5 |

마이그레이션을 만들지 않았으므로 `flask db heads` 는 해당 없다(백엔드 파일 0개 변경).

## 2. 바뀐 파일

**새로 만든 것**

| 파일 | 역할 |
|---|---|
| `mobile/lib/analytics/analytics_event.dart` | 이벤트 4개의 이름·파라미터를 만드는 순수 함수 + `AnalyticsEvent` |
| `mobile/lib/analytics/analytics_service.dart` | `AnalyticsService` 인터페이스 · `NoopAnalyticsService` · `firebaseBootstrapProvider` · `analyticsServiceProvider` |
| `mobile/lib/analytics/firebase_analytics_service.dart` | Firebase 구현(외부 호출 한 줄을 함수로 끊어 둬 테스트가 본다) |
| `mobile/lib/puzzle/share_text.dart` | `shareUrl`·`shareDate`·`maskShareText`·`shareGrid`·`buildShareText`(전부 순수) |
| `mobile/lib/puzzle/today_stats_provider.dart` | `todayStatsProvider`(`isAutoDispose`) |
| `mobile/lib/share/share_sheet.dart` | `share_plus` 래퍼 + `shareTextProvider` |
| `mobile/lib/widgets/result_sheet.dart` | `showResultSheet` · `ResultSheet`(헤더·요약 타일·통계·카운트다운·버튼·연결 안내) |
| `mobile/lib/widgets/stat_bar.dart` | `StatBar`(OVERRIDES §6 컴포넌트) |
| `mobile/lib/widgets/puzzle_countdown.dart` | 1초 틱 카운트다운(시계 주입) |
| `mobile/test/analytics/*`(2) · `test/puzzle/share_text_test.dart` · `test/widgets/puzzle_countdown_test.dart` · `test/widgets/result_sheet_test.dart` · `test/widgets/result_sheet_tablet_test.dart` · `test/golden/result_sheet_golden_test.dart` + PNG 3장 | 테스트·골든 |

**고친 것**

| 파일 | 변경 |
|---|---|
| `mobile/lib/api/api_client.dart`·`dio_api_client.dart`·`api_models.dart` | `fetchTodayStats` + `TodayStats` 모델 |
| `mobile/lib/screens/today_tab.dart` | "결과 보기" 활성화 · 제출로 끝나면 시트 + `puzzle_complete` · "퍼즐 없음" 카드가 `PuzzleCountdown` 사용 |
| `mobile/lib/puzzle/guess_rules.dart` | `attemptsUsed(puzzle)` 추가 |
| `mobile/lib/main.dart` | Firebase 부팅 결과를 `firebaseBootstrapProvider` 로 넘김 |
| `mobile/lib/theme/app_theme.dart` | `dialogTheme`(태블릿 다이얼로그 면·모서리) 추가 |
| `mobile/assets/translations/{ko,en}.json` | `result.*`·`share.*` 추가(키 집합 동일) |
| `mobile/pubspec.yaml`·`pubspec.lock` | `share_plus: ^13.3.1` |
| `mobile/test/fakes/fake_api_client.dart` | `fetchTodayStats` + `fakeTodayStats` + 게이트·오류·호출 수 |
| `mobile/test/screens/today_tab_test.dart` | 하네스에 analytics 주입 + "결과 시트(S2)" 그룹 4개 |
| `README.md` | "설계 판단" 끝에 `### 26.` |
| `.scratch/store-launch/spec.md` | "미정 항목" 끝에 미정 20 확정 줄 — **티켓이 명시적으로 시킨 수정** |

`.env.example`·`docs/RELEASE.md`·README API 표는 **바꾸지 않았다**: 이 티켓이 더할
설정값이 없고, `GET /api/v1/puzzles/today/stats` 는 이미 표에 있다.

## 3. 테스트 (red → green 으로 쓴 순서)

전부 **가짜 `ApiClient`·주입한 공유 함수·no-op Analytics** 만 두고 실제 위젯을
그린다. 네트워크·플랫폼 채널·스토어·Firebase 는 한 번도 타지 않는다.

### 3.1 API 경계 (red 먼저: `TodayStats` 없음 → 컴파일 실패)

`dio_api_client_test.dart` 는 가짜 `HttpClientAdapter` 로 **보낸 요청**을 본다:
경로 `/puzzles/today/stats`, GET, `Authorization: Bearer …`, **쿼리 없음**(언어를
안 보낸다). 404 `NO_PUZZLE_TODAY` 는 기존 분기를 그대로 타 `NoPuzzleTodayApiException`
으로 온다. `api_models_test.dart` 는 `by_attempt` 가 문자열 키로 오는 걸 int 키
표로 바꾸는 것, 정수 `0` 도 double 로 읽는 것, 숫자가 아닌 키를 버리는 것을 본다.

### 3.2 공유 텍스트(순수 함수)

`share_text_test.dart`: 빈 타일 `_` 펼침과 구분자 유지(`R_D F`), 🟩/⬜ 격자,
줄 구성(머리글/가림/결과/빈 줄/격자/빈 줄/링크), 시도 0개면 격자 줄 없음,
`utm_source=share`, ISO 날짜. **정답이 들어가지 않는 것**은 위젯 테스트가 본다
(`isNot(contains('지하철역'))`).

### 3.3 카운트다운(가짜 시계)

`puzzle_countdown_test.dart`: UTC 14:47:27 → KST 23:47:27 → `00:12:33`(기기
시간대와 무관), 시계를 1초 밀고 `pump(1초)` 하면 `00:12:32`, 위젯이 사라지면
타이머가 멈춘다(남아 있으면 테스트 프레임워크가 실패시킨다).

### 3.4 결과 시트(18개)

헤더 4개(성공/실패/정답 없음/en), 분포 6개, 카운트다운 1개, 공유 3개, 순위 1개,
연결 안내 1개, 다크모드·글자 1.3배 2개. 분포의 "내 행" 은 색 토큰 값
(`primaryButton` vs `mutedForeground`)과 글자 굵기를 **둘 다** 본다 — 색만으로
구분하지 않는다는 규칙이 코드에 남아 있는지 확인하는 테스트다. 막대 길이는
트랙 폭 × 비율(±0.5px)로 잰다.

### 3.5 분석(9개)

이름 표 4개(파라미터 값이 String·num 뿐인 것 포함), 서비스 5개(no-op 기록 순서,
Firebase 가 이름·파라미터를 그대로 넘기는지, `firebaseBootstrapProvider` 값으로
구현이 갈리는지, 아무것도 안 덮으면 no-op 인지).

### 3.6 오늘 탭 ↔ 시트(4개)

제출로 끝나면 시트가 뜨고 `puzzle_complete {language: ko, success: 1, attempts: 2}`
가 한 번 찍힌다(통계도 1회 조회). 마지막 시도가 오답이면 `success: 0, attempts: 5`.
아직 안 끝난 제출은 시트도 이벤트도 없다. **이미 끝난 퍼즐을 열면 자동으로 뜨지
않고, "결과 보기" 로 열어도 이벤트는 안 찍힌다**(다른 기기에서 끝낸 퍼즐 경로).

### 3.7 태블릿 T2(6개)

390 바텀시트 / 744·1024 다이얼로그, 다이얼로그 폭 ≤560·가운데(x=372)·상하 여백
≥48, 744 에서 분포·카운트다운·버튼이 다 있고 **공유 텍스트와 순위 동작이 폰과
같다**, 손잡이는 바텀시트에만.

### 3.8 응답 경합 (코디네이터 메모 — 25 의 구조를 따를 것)

**이 티켓은 서버 쓰기를 하지 않고 조회가 하나뿐이라 25 의 세대 번호가 필요한
경합이 생기지 않는다.** 시트는 열 때의 퍼즐 **스냅숏**을 그리고(끝난 퍼즐이라
그 뒤로 바뀌지 않는다) `todayPuzzleProvider` 를 다시 보지 않으므로, 늦게 온
오늘 퍼즐 응답이 시트 내용을 과거로 되돌릴 자리가 없다. 분포 조회는
`todayStatsProvider`(Riverpod `FutureProvider`) 한 곳이라 재시도(`invalidate`)가
겹쳐도 프레임워크가 마지막 요청만 상태에 쓴다. 제출은 그대로 25 의
`TodayPuzzleNotifier` 가 하고, 이 티켓은 **그 결과를 읽기만** 한다 —
`_submit` 이 상태를 다시 읽어 "이번 응답으로 finished 가 됐는가" 를 볼 뿐이다.

### 3.9 실행 결과

```
$ cd mobile && dart format --set-exit-if-changed .     # CI 는 `lib test`, 둘 다 돌렸다
Formatted 85 files (0 changed) in 0.22 seconds.     # exit 0

$ flutter analyze
No issues found! (ran in 3.4s)

$ flutter test
00:30 +256: All tests passed!                        # 이 티켓이 더한 54개 포함

$ JAVA_HOME=/opt/homebrew/opt/openjdk@17 flutter build apk --debug
✓ Built build/app/outputs/flutter-apk/app-debug.apk

$ flutter build ios --no-codesign --debug
Running pod install...   4.2s
✓ Built build/ios/iphoneos/Runner.app                # share_plus pod 등록 확인
```

빌드 뒤 `mobile/build`(2.8G)·`mobile/ios/Pods`(68M)·`ios/Podfile.lock` 을 지웠고,
`pod install` 이 건드린 `ios/Runner.xcodeproj/project.pbxproj`·
`contents.xcworkspacedata` 는 되돌렸다(이 티켓의 변경이 아니다).

백엔드는 코드를 한 줄도 안 바꿨지만 rebase 로 base 가 바뀌어 한 번 더 돌렸다
(전용 자원: DB `chosung_daily_test_t26`, Redis DB 14, 마이그레이션 DB
`chosung_daily_test_t26_migrations`).

```
$ uv run ruff check .
All checks passed!

$ TEST_DATABASE_URL=…/chosung_daily_test_t26 TEST_REDIS_URL=redis://127.0.0.1:6379/14 \
  TEST_MIGRATION_DATABASE_URL=…/chosung_daily_test_t26_migrations uv run pytest -q
1110 passed in 720.86s (0:12:00)
```

공용 `chosung_daily_test`·Redis DB 1 과 다른 워커의 DB(t25·t27·t34)는 건드리지
않았다. `ruff format` 은 CI 가 쓰지 않아(`.github/workflows/ci.yml` 은 `ruff check`
뿐) 돌리지 않았다 — 돌리면 이 티켓과 무관한 54개 파일이 바뀐다.

## 4. `audit.native` 체크리스트 (impeccable `reference/audit.native.md`)

브라우저 도구·`impeccable detect` 는 쓰지 않는다(HTML/CSS 용). 22·24·25 와 같이
소스를 `reference/ios.md`·`android.md` 기준으로 읽고 5축에 점수를 매겼다. 폭 확인은
눈이 아니라 위젯 테스트(390·744·1024)와 골든 3장이다.

| # | 축 | 25 | 26 | 핵심 소견 |
|---|---|---|---|---|
| 1 | Accessibility | 4 | **4** | 분포 막대가 "2회 31퍼센트 내 결과" 로 읽힌다(색·굵기로만 내 행을 말하지 않는다). 제목·"오늘의 통계" 는 `Semantics(header: true)` — 목업 detect 가 잡은 "같은 크기 h 태그" 를 시맨틱 헤딩으로 해결했다. 요약 타일은 보드와 같은 "글자 + 맞음/아님" 레이블, 스켈레톤·손잡이는 `ExcludeSemantics`/장식. 버튼·닫기(IconButton)는 테마 최소 44 이상, 닫기엔 `tooltip` 이 붙어 레이블이 있다. 글자 1.3배 테스트 통과(그때 넘치던 카운트다운 줄을 `Flexible` 로 고쳤다 — §6) |
| 2 | Performance | 3 | 3 | 시트 내용은 최대 5행 × 8칸 + 막대 5줄이라 가상화가 필요 없다. 통계는 시트를 열 때 1회 조회(`fetchTodayStatsCalls == 1` 로 확인), 카운트다운만 1초마다 그 한 줄을 다시 그린다(`PuzzleCountdown` 아래 트리만 rebuild). 전면 광고·SDK 는 티켓 31 |
| 3 | Appearance & Theming | 4 | **4** | 새 위젯 전부 `AppColors` 토큰만 쓴다(raw hex 는 여전히 `app_colors.dart` 한 파일뿐, 골든 라이트/다크 2장으로 확인). 다이얼로그가 테마에 없어 바텀시트와 다른 면을 쓰던 걸 `dialogTheme` 로 맞췄다 |
| 4 | Platform Conformance | 3 | 3 | Material `showModalBottomSheet`/`showDialog`, `FilledButton`/`OutlinedButton`/`IconButton` 기본 컨트롤. 공유는 **OS 공유 시트**(`share_plus` → iOS `UIActivityViewController`, Android `ACTION_SEND`)라 앱이 자체 공유 UI 를 그리지 않는다. 시스템 back·edge-swipe·드래그로 닫기를 그대로 둔다(`isDismissible` 기본값). 아이콘 Lucide 는 OVERRIDES §8 의 의도된 이탈(22 부터) |
| 5 | Adaptivity | 4 | **4** | T2 분기(바텀시트/다이얼로그)를 `showAdaptiveSheet` 한 곳에서만 판정하고 내용 위젯은 하나다. 내용은 `SingleChildScrollView` 라 작은 폰·큰 글자에서 잘리지 않고, 다이얼로그는 상하 48 여백 안에서 스크롤된다. 폭 390·744·1024 테스트 + 골든 3장 |
| **합계** | | **18/20** | **18/20** | **Excellent (minor polish)** |

**추가 항목 "태블릿 폭 포함": 통과.** 744·1024 는 `result_sheet_tablet_test.dart`
가, 1366·834·320 은 24 의 셸 테스트가 덮는다(결과 시트는 `showAdaptiveSheet` 의
같은 분기를 타고, 그 분기는 24 의 `adaptive_sheet_test.dart` 가 600 경계까지 본다).

### 목업 `e2_result` 대비 기록

| 항목 | 목업 | 구현 | 판단 |
|---|---|---|---|
| 제목·부제 | "정답은 지하철역!" / "3번째 시도만에 성공하셨습니다" | 같은 구성("2번째 시도에 맞췄어요") | 그대로 |
| 시도 요약 | 미니 타일 3행 고정 | 실제 시도 수만큼(1~5행) | 데이터에 맞춤 |
| 분포 막대 | 남의 막대가 트랙과 같은 `#E7E5E4` 라 **안 보인다** | 트랙 `muted`, 남 `mutedForeground`, 내 행 `primary-button` | 목업 수정 — 보이지 않는 막대는 정보가 아니다 |
| 내 행 강조 | 검정 막대 + 굵은 글자 | 같음(`primary-button`) | 그대로. SCREENS 의 "brand 색" 은 OVERRIDES §2(면 채움 금지) 우선 |
| 카운트다운 | 시계 아이콘 + "다음 퍼즐까지 07:12:33" | 같음(Lucide `clock`) | 아이콘 세트만 OVERRIDES §8 |
| 버튼 | 검정 "결과 공유" + outline "순위 보기" | 같음(테마 `primary-button`, 모서리 10) | 그대로 |
| 하단 안내 | "기록을 지키려면 계정을 연결하세요 →" + ✕ | 같음(동작·1회 플래그는 29) | 자리만 |
| 배경 | dimmed 게임 캔버스 + 하단 탭 바 | 실제 S1 보드 위에 뜬다 | 목업은 한 장짜리 목업이라 그렇게 그린 것 |
| 아이콘 | Material Symbols | Lucide | OVERRIDES §8 |
| detect 메모 | "h 태그 동일 크기 1건 — 구현 시 시맨틱 헤딩으로 해결" | `Semantics(header: true)` 2곳 | 해결 |

## 5. 골든 3장

`mobile/test/golden/result_light_390.png`·`result_dark_390.png`·
`result_tablet_744.png`. 카운트다운은 가짜 시계(`now`)로 `07:12:33` 에 고정했다 —
안 그러면 초가 흘러 골든이 매번 달라진다. 생성·갱신은
`flutter test test/golden --update-goldens`, 지금은 `--update-goldens` 없이 통과한다.

## 6. 이 티켓이 고친 실제 결함 2건 (테스트가 잡았다)

1. **분포 막대가 높이 0 이었다.** `FractionallySizedBox(widthFactor:)` 만 주면
   `ColoredBox` 가 느슨한 세로 제약에서 0 높이로 접힌다 — 막대가 아예 안 보였다.
   `heightFactor: 1` + `alignment: centerLeft` 로 고쳤고 "막대 길이가 비율에
   비례한다" 테스트(높이도 같이 본다)가 지킨다. 위젯 트리에는 멀쩡히 있어서
   존재만 보는 테스트로는 못 잡는다.
2. **en 에서 카운트다운 줄이 0.78px 넘쳤다.** "Next puzzle in 00:12:33" 이 한 줄에
   안 들어가 `RenderFlex overflowed`. `Flexible` 로 감싸 줄바꿈을 허용했다.
   ko 만 보고 끝냈으면 영어 기기에서만 노란 줄무늬가 났다.

## 7. 숨기지 않는 것

- **실기기·시뮬레이터에서 띄우지 않았다.** 골든은 Flutter 테스트 렌더러가 그린
  그림이다. **네이티브 공유 시트가 실제로 뜨는지, 공유 텍스트의 이모지가 기기에서
  어떻게 보이는지는 이 티켓이 확인하지 못했다** — 티켓 35·36 의 사람 체크리스트가
  받아야 한다. 테스트는 `share_plus` 를 provider 뒤에서 가로채 "무슨 텍스트가
  나갔는지" 까지만 본다.
- **Firebase 에 이벤트가 실제로 도착하는지는 확인하지 못했다.** 설정 파일이 없는
  빌드라 `initializeFirebase` 가 건너뛰고 no-op 구현이 돈다. Firebase 구현은
  "이름·파라미터를 `logEvent` 에 그대로 넘긴다" 까지만 테스트했다(D0 에서 설정
  파일이 들어온 뒤 콘솔 DebugView 로 확인할 일이다).
- **전면 광고(OVERRIDES §5 — 시트가 완전히 뜬 뒤 1회)는 넣지 않았다.** 광고 SDK 가
  티켓 31 이다. 시트를 띄우는 자리(`TodayTab._openResult`)가 그 훅이 들어갈 곳이다.
- **"기록을 지키려면 연결하세요" 는 자리와 닫기만이다.** 눌렀을 때의 연결 흐름과
  "퍼즐당 1회" 플래그(지금은 시트가 살아 있는 동안만 기억)는 티켓 29 다. US 20 의
  "한 번만" 은 아직 보장되지 않는다.
- **"순위 보기" 는 순위 탭으로 보내기만 한다.** 그 탭의 내용(S3)은 티켓 27 이다.
- **`paywall_view`·`subscribe_start` 는 정의만 있고 아무도 안 부른다**(티켓 32).
  이름 표 테스트가 두 이벤트의 이름을 고정해 둔 상태다.
- **`ruff format` 은 돌리지 않았다**(§3.9). CI 가 쓰지 않고, 돌리면 이 티켓과
  무관한 54개 파일이 바뀐다.
- **골든은 이 기계(macOS, Flutter 3.38.6)에서 만든 파일이다.** 렌더러가 바뀌면
  차이가 날 수 있고, 그때는 `--update-goldens` 로 다시 찍고 사람이 본다.
