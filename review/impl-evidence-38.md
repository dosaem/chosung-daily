# 티켓 38 구현 증거 — 리더보드 익명 이름 언어 중립화 + en 복수형

**브랜치:** `dosaem/t38-leaderboard-name-i18n` · **날짜:** 2026-10-15
**기준:** 로컬 `main` (`8ddc8fd`) 위에 쌓았다. 마이그레이션 변경 0건
(`git diff main -- migrations/` 가 비어 있고 `flask db heads` 는 `b1c7d4e0a932` 하나).

## 0. 한 줄 요약

리더보드 응답에서 서버가 만들던 표시 문자열 `display: "게스트 #a3f1"` 을 **언어 중립
태그** `anon_tag: "a3f1"` 로 바꾸고, "게스트 #" / "Guest #" 접두사는 웹·앱이 자기 UI
언어로 붙이게 했다. 같은 결함 계열인 en 복수형(`1 tries`)은 앱 4개 키를
easy_localization `plural` 로, 웹 3개 문구를 사전 `attempts_one`/`attempts_other` +
번들 `attemptsText()` 로 고쳤다. 하위 호환 `display` 는 남기지 않고 지웠다 — 근거는
§2.

## 1. 티켓 체크박스 ↔ 증거

| 티켓 Change / Acceptance | 증명하는 테스트·명령 | 위치 |
|---|---|---|
| 1. 서버가 언어 중립 익명 식별자를 담는다 | `tests/test_leaderboard.py::test_anon_tag_is_guest_id_in_four_hex_digits`, `::test_leaderboard_entries_do_not_leak_guest_id`(필드 집합) | §3.1 |
| 1. 서버 응답에 한글 접두사가 없다 | `tests/test_leaderboard.py::test_the_leaderboard_response_carries_no_ui_language` — 응답 **본문 전체**에 `[가-힣]` 없음 | §3.1 |
| 1. `display` 유지/제거 판단 + README `### 38.` 근거 | README "38." 3번째 단락(배포 모양 근거), 이 문서 §2 | §2 |
| 1. 이메일·게스트 ID 원본 비노출 원칙 유지 | 같은 파일 `::test_leaderboard_entries_do_not_leak_guest_id` — `set(entry) == {rank, anon_tag, attempts, seconds, is_me}` | §3.1 |
| 1. README API 표 갱신 | `README.md:87` 의 리더보드 행 | §5 |
| 2. 웹이 UI 언어로 `게스트 #a3f1` / `Guest #a3f1` 를 그린다 | `tests/test_web_js.py::test_korean_ui_prefixes_the_anon_tag_with_the_korean_word`, `::test_english_ui_prefixes_the_same_tag_with_guest` (실제 번들을 node 로 돌린 렌더) | §3.2 |
| 2. 웹 `is_me` 기존 동작 유지 | `::test_my_row_is_still_marked_by_a_class_not_by_a_different_name` — 이름 규칙은 남의 행과 같고 표기는 `is-me` 클래스 | §3.2 |
| 3. 앱 `ranking_tab.dart` + semantics 가 번역 키로 이름을 만든다 | `mobile/test/screens/ranking_tab_test.dart` "ko: 태그에 …", "en: 같은 태그에 …", "en/ko: 행 semantics 라벨 …" | §3.3 |
| 3. 골든이 바뀌면 다시 뜬다 | **바뀌지 않았다** — ko 렌더가 글자까지 같아서 `ranking_light_390.png`·`ranking_tablet_1024.png` 가 그대로 통과 | §3.3 |
| 4. en 복수형 `1 try` / `N tries`, ko 그대로 | 앱: `ranking_tab_test.dart` "en: 시도 횟수는 1 에서 단수, 2 이상에서 복수다" · "ko: 시도 횟수 문구는 1 과 2 에서 같다". 웹: `test_web_js.py::test_english_attempts_are_singular_at_one_and_plural_above` · `::test_korean_attempts_read_the_same_at_one_and_above` | §3.2·§3.3 |
| 5. 전체 pytest · ruff | §4.1 | §4.1 |
| 5. `flutter analyze` · `flutter test` · `dart format` | §4.2 | §4.2 |
| 5. `flutter build apk --debug` exit 0 (빌드 후 `mobile/build` 삭제) | §4.3 | §4.3 |
| 5. 웹 변경 → `impeccable detect` 0건 | §4.4 — ko/en × light/dark 4장 각각 0건, 320px·390px 패스도 exit 0 | §4.4 |

## 2. 설계 판단: `display` 를 남기지 않고 지웠다

티켓이 "하위 호환을 위해 남길지, 제거할지 판단" 하라고 했다. **제거**를 골랐다.

**남기면 같은 이름의 정본이 둘이 되고, 둘 중 하나는 영어 화면에서 틀린 값이다.**
"안 쓰는 필드" 하나가 다음 클라이언트에서 다시 쓰이면 이 티켓이 고친 결함이 그대로
돌아온다. 하위 호환 필드의 값으로 뭘 넣어도 — 한국어로 두면 영어 UI 가 그걸 읽는
순간 결함 재발이고, 영어로 두면 한국어 UI 가 깨진다 — UI 언어를 모르는 서버가
만들 수 있는 올바른 표시 문자열이 애초에 없다.

**지워도 되는 근거는 배포 모양이다.**

| 클라이언트 | 배포 경로 | 옛 필드를 읽는 바깥 인스턴스 |
|---|---|---|
| 웹 | 서버와 **같은 저장소·같은 배포**. Flask 가 `web/static/app.js` 를 직접 서빙하고, 정적 URL 에 프로세스 시작 시각이 `?v=` 로 붙어(`app/__init__.py:33`) 배포마다 캐시가 새로 받아진다 | 없음 |
| 앱 | **아직 스토어 미출시** | 없음 |

티켓 07 이 `guest_id`·`solved_in_seconds` 를 같은 식으로 지운 선례도 있다
(스펙 §API 표: "기존 `guest_id`·`solved_in_seconds` 제거").

**남는 위험 한 가지:** 배포 **순간에 이미 열려 있던 탭**은 메모리에 옛 JS 를 들고
새 응답을 받는다 — `entry.display` 가 `undefined` 라 이름 칸에 `undefined` 가 찍힌다.
새로고침 한 번으로 끝나고, 출시 전이라 그런 탭의 수가 0 에 가깝다. 하위 호환 필드를
영구히 들고 가는 비용과 맞바꿀 만하다고 봤다. (이 `undefined` 는 추측이 아니라
실제로 봤다 — 구현 전 red 단계에서 새 테스트가 `#1undefined · 1 tries · 00:00:41`
을 돌려줬다. §3.2)

## 3. 바뀐 것과 그걸 잡는 테스트

### 3.1 서버 — `display_name()` → `anon_tag()`

| 파일 | 변경 |
|---|---|
| `app/services/puzzle_metrics.py` | `display_name(guest_id) -> "게스트 #a3f1"` → `anon_tag(guest_id) -> "a3f1"`. 상수 `DISPLAY_ID_MODULUS` → `ANON_TAG_MODULUS`(이름이 값과 맞게). `% 0x10000` 자르기와 충돌 허용은 그대로 |
| `app/schemas/leaderboard.py` | `LeaderboardEntry.display: str` → `anon_tag: str` |

`_my_rank`(= 응답 `me`)는 손대지 않았다 — 이름 필드가 없다.

```
$ uv run pytest -q tests/test_leaderboard.py
........                                                                 [100%]
8 passed in 6.86s
```

새 테스트 `test_the_leaderboard_response_carries_no_ui_language` 는 필드 하나가 아니라
**응답 본문 전체**에 한글이 없는지 본다. 필드만 보면 다음에 또 서버에서 라벨을
만들 때 같은 결함이 조용히 돌아온다.

### 3.2 웹 — 접두사·복수형을 사전에서 만든다

| 파일 | 변경 |
|---|---|
| `app/utils/ui_strings.py` | 새 키 `leaderboard_guest`(`게스트 #{tag}` / `Guest #{tag}`), `attempts_one`·`attempts_other`. `leaderboard_entry`·`my_rank`·`stats_row` 는 숫자 대신 **완성된 문구**를 받는다(`{display}`→`{name}`, `{attempts}회`/`{attempts} tries`→`{attempts}`) |
| `web/static/app.js` | `t()` 옆에 `attemptsText(count)`·`guestName(anonTag)` 두 함수. `renderLeaderboard`·`my-rank`·`renderTodayStats` 가 그걸 쓴다 |

ko 사전은 `attempts_one` 과 `attempts_other` 가 같은 값(`{count}회`)이다 — 부르는 쪽이
언어를 묻지 않게 두 키를 양쪽에 다 뒀고, `tests/test_ui_strings.py` 가 "ko 는 두 형태가
같다 / en 은 다르다" 를 못 박는다.

**구현 전 red 단계**(새 시나리오 `tests/js/leaderboard_names.mjs` 를 먼저 두고 서버만
바꾼 상태):

```
E         - #1Guest #a3f1 · 1 try · 00:00:41
E         + #1undefined · 1 tries · 00:00:41
```

한 줄에 이 티켓의 결함 두 개가 다 있다 — 서버 필드 이름이 바뀌어 `undefined`,
그리고 1 회인데 `1 tries`.

구현 후:

```
$ uv run pytest -q tests/test_web_js.py tests/test_ui_strings.py tests/test_web.py
........................................................................ [ 76%]
......................                                                   [100%]
94 passed in 33.28s
```

새 시나리오는 **작업 트리의 번들을 node 로 실제 실행**해서 행 텍스트를 읽는다
(`tests/js/harness.mjs`, 기존 방식 그대로). 사전에 키가 있는지만 보는 문자열 계약으로는
`1 tries` 가 안 잡힌다 — `t()` 호출 한 번으로는 단수·복수가 갈리지 않으니 렌더 결과를
봐야 드러난다.

`tests/test_web.py` 의 번들 계약 테스트도 이름을 바꿨다
(`test_js_renders_leaderboard_display_is_me_and_my_rank` →
`…_name_is_me_and_my_rank`): `entry.anon_tag` 가 있고 `entry.display` 는 **없어야**
한다는 쪽으로 뒤집었다.

### 3.3 앱 — 번역 키가 이름을, `plural` 이 복수형을 만든다

| 파일 | 변경 |
|---|---|
| `mobile/lib/api/api_models.dart` | `LeaderboardEntry.display` → `anonTag`, `json['anon_tag']` |
| `mobile/lib/screens/ranking_tab.dart` | 행 이름을 `'ranking.guest'.tr(namedArgs: {'tag': entry.anonTag})` 로. 내 순위 카드 `ranking.attempts` 를 `.plural()` 로 |
| `mobile/lib/widgets/leaderboard_row.dart` | `attemptsLabel` 을 `.plural()` 로 — 시도 칸과 `row_semantics` 라벨이 같은 문구를 쓴다 |
| `mobile/assets/translations/{ko,en}.json` | `ranking.guest` 추가. `ranking.attempts`·`result.stats_row`·`streak.days`·`streak.puzzles` 를 plural 객체로 |
| `mobile/lib/screens/records_tab.dart`, `today_tab.dart`, `widgets/stat_bar.dart` | 그 네 키의 호출부를 `.tr()` → `.plural()` |

`ranking.me`(하단 고정 내 행의 "나"/"You")는 원래 번역 키였으니 그대로다.

**ko 에 `one` 을 적지 않아도 되는 이유**(README "38." 에도 적었다): easy_localization
3.0.8 은 `ignorePluralRules` 기본값 `true` 에서 1→`one`·2→`two`·그 밖→`other` 를
찾고, **없는 형태는 `other` 로 눕힌다**(`Localization._resolvePlural`). 그래서 ko 의
`other` 하나가 모든 수를 받고, en 에 `two` 가 없어도 `other`(`2 tries`)로 떨어진다.
`fallbackLocale` 이 `ko` 인 것도 안전하다 — ko 에 `one` 이 없으니 en 이 한국어 단수를
주워올 경로가 없다.

**골든은 다시 뜨지 않았다.** ko 렌더가 글자까지 같아서
(`게스트 #a3f1` 그대로, `{count}회` 그대로) `ranking_light_390.png`·
`ranking_tablet_1024.png`·`today_*`·`result_*`·`records_*` 가 전부 그대로 통과했다.
en 은 골든이 없고 위젯 테스트가 본다.

### 3.4 공유 문서

| 파일 | 변경 |
|---|---|
| `README.md` | API 표 리더보드 행(`display`→`anon_tag`), 새 절 `### 38.`, 그리고 `### 07.` 끝에 **"티켓 38 이 이 절의 결론을 뒤집었다"** 한 블록 |
| `CONTEXT.md` | 용어집 "리더보드" 정의 한 문장 — 서버는 태그만 주고 화면이 접두사를 붙인다 |

`### 07.` 를 건드린 건 그 절이 *"서버가 표시 문자열까지 만들어서 보낸다"* 를 근거까지
적어 뒀기 때문이다. 그대로 두면 다음에 읽는 사람이 뒤집힌 결론을 따라간다. 07 의
본문은 지우지 않고 인용 블록 한 개만 덧붙였다.

`.env.example`·`docs/RELEASE.md` 는 **변경하지 않았다** — 새 환경변수도, 사람이 할
배포 절차도 없다.

### 3.5 테스트 자원

전용 자원만 썼다. 공용 테스트 DB·Redis 는 건드리지 않았다.

| 변수 | 값 |
|---|---|
| `TEST_DATABASE_URL` | `chosung_daily_test_t38` (이 티켓용으로 새로 만들었다 — root 로 `CREATE DATABASE … ; GRANT ALL ON … TO 'chosung'@'%'`) |
| `TEST_MIGRATION_DATABASE_URL` | `chosung_daily_test_t38_migrations` (같이 새로) |
| `TEST_REDIS_URL` | Redis DB **14** |

같은 worktree 에서 pytest 를 동시에 두 개 돌리지 않았다. 접속 정보 값은 이 문서에
적지 않는다.

## 4. 직접 실행한 명령과 출력

### 4.1 백엔드 — 전체 pytest · ruff

```
$ TEST_DATABASE_URL='…/chosung_daily_test_t38?charset=utf8mb4' \
  TEST_REDIS_URL='redis://127.0.0.1:6379/14' \
  TEST_MIGRATION_DATABASE_URL='…/chosung_daily_test_t38_migrations?charset=utf8mb4' \
  uv run pytest -q
........................................................................ [ 96%]
............................................                             [100%]
1412 passed in 1416.64s (0:23:36)                                 # exit 0

$ uv run ruff check .
All checks passed!                                                # exit 0
```

1412개 중 이 티켓이 더한 건 **9개**(기준 1403 — 티켓 28 과 같은 수):

| 파일 | 더한 테스트 |
|---|---|
| `tests/test_leaderboard.py` | 1 — 응답 본문 전체에 한글이 없다. (그 밖에 `display`→`anon_tag` 로 고친 어서션 4곳, 테스트 1개 이름 변경) |
| `tests/test_web_js.py` | 5 — ko/en 이름 2, en/ko 복수형 2, `is_me` 표기 1 |
| `tests/test_ui_strings.py` | 3 — en 단·복수 쌍, 리더보드 문구의 자리표시자 모양, 접두사 번역 |

`ruff format --check` 는 **돌리지 않았다** — 레포가 쓰지 않는 검사다(현재 `main`
에서도 60개 파일이 "would be reformatted" 로 나온다). 이 프로젝트의 린트 게이트는
`ruff check` 다.

23분이 걸린 건 공용 MySQL 컨테이너를 다른 워크트리 두 곳(`t29`·`t30`)이 같이 쓰고
있어서다. 테스트 DB 는 서로 다르다(§3.5).

### 4.2 Flutter

```
$ cd mobile && flutter analyze
Analyzing mobile...
No issues found! (ran in 2.4s)                                    # exit 0

$ cd mobile && dart format --set-exit-if-changed lib test
Formatted 122 files (0 changed) in 0.17 seconds.                  # exit 0

$ cd mobile && flutter test
00:30 +403: All tests passed!                                     # exit 0
```

403개 중 이 티켓이 더한 건 **10개**(기준 393):

| 파일 | 더한 테스트 |
|---|---|
| `test/screens/ranking_tab_test.dart` | 7 — ko/en 이름 2, en/ko 복수형 2, 내 순위 단수 1, ko/en 행 semantics 2 |
| `test/screens/records_tab_test.dart` | 2 — `streak.days`·`streak.puzzles` 의 en 단/복수와 ko 동일성 |
| `test/widgets/result_sheet_test.dart` | 1 — 분포 막대 semantics 라벨의 en 복수형(`result.stats_row`) |

나머지는 회귀 확인이고, 골든 11장이 전부 그대로 통과했다(§3.3). `streak.*` 와
`result.stats_row` 는 호출부를 `.plural()` 로 바꿨는데 기존 테스트가 ko 만 봐서
en 단수를 증명하지 못했다 — 그래서 저 3개를 더했다.

### 4.3 Android 디버그 빌드

```
$ cd mobile && flutter build apk --debug
Running Gradle task 'assembleDebug'...                             41.4s
✓ Built build/app/outputs/flutter-apk/app-debug.apk               # exit 0

$ rm -rf mobile/build      # 요구대로 삭제, git status 에 흔적 없음
```

### 4.4 웹 `impeccable detect` — ko/en × light/dark 0건

번들이 **실제로 그리는** 마크업으로 스냅샷을 만들어 돌렸다. 재현 스크립트를
레포에 남겼다:

- **`review/web-detect-snapshots-38.py`** — 실제 템플릿을 Flask 로 렌더하고, CDN
  폰트·정적 링크를 떼고 `tokens.css`·`style.css` 를 인라인하고, 순위 섹션을 펼친 뒤
  행을 끼운다.
- **`review/web-detect-rows-38.mjs`** — 그 행 마크업을 `tests/js/harness.mjs` 로
  번들을 실제 실행해서 꺼낸다. 손으로 다시 적으면 그건 번들이 그리는 화면이 아니다.

```
$ uv run python review/web-detect-snapshots-38.py <출력 디렉터리>
en-dark.html  en-light.html  ko-dark.html  ko-light.html

$ (cd <출력 디렉터리> && python3 -m http.server 9438 &)

$ ~/.impeccable/bin/0.1.14/impeccable detect \
    http://127.0.0.1:9438/ko-light.html http://127.0.0.1:9438/ko-dark.html \
    http://127.0.0.1:9438/en-light.html http://127.0.0.1:9438/en-dark.html
EXIT=0                      # 출력 없음

$ for p in ko-light ko-dark en-light en-dark; do
    ~/.impeccable/bin/0.1.14/impeccable detect --json http://127.0.0.1:9438/$p.html
  done   # findings 개수
ko-light: 0 findings
ko-dark:  0 findings
en-light: 0 findings
en-dark:  0 findings

$ ~/.impeccable/bin/0.1.14/impeccable detect --viewport 320x844 \
    http://127.0.0.1:9438/en-light.html http://127.0.0.1:9438/en-dark.html
EXIT320=0

$ ~/.impeccable/bin/0.1.14/impeccable detect --viewport 390x844 \
    http://127.0.0.1:9438/en-light.html http://127.0.0.1:9438/ko-light.html
EXIT390=0
```

스냅샷에 넣은 보드는 1위 1회 / 2위 2회(내 행) / 3위 2회 / 4위 3회 / 5위 5회·1시간
넘김이다 — 단수·복수·`is-me` 면·3위까지 굵은 순위·시간 자리수가 한 화면에 다 들어간다.

**다크모드 처리:** `detect` 에 색상 모드 옵션이 없어서, 다크 스냅샷은
`@media (prefers-color-scheme: dark)` 를 `@media all` 로 바꿔 토큰의 다크 선언을
조건 없이 켰다. 보는 색은 우리 다크 토큰 그대로다(브라우저 반전이 아니다 —
티켓 18 리뷰가 `--force-dark-mode` 를 쓰지 않은 것과 같은 이유).

**검증하지 않은 것:** CDN Pretendard 폰트(스냅샷에서 떼어 냈다 — 로컬 폴백으로
렌더됐다), iOS Safari 네이티브 스마트 배너, 실제 스토어 배지 아트워크.

## 5. 바뀐 파일 전체

```
 CONTEXT.md                                         |   2 +-
 README.md                                          |  58 ++++++++++-
 app/schemas/leaderboard.py                         |   4 +-
 app/services/puzzle_metrics.py                     |  18 ++--
 app/utils/ui_strings.py                            |  22 ++--
 mobile/assets/translations/en.json                 |  21 +++-
 mobile/assets/translations/ko.json                 |  17 ++-
 mobile/lib/api/api_models.dart                     |  13 ++-
 mobile/lib/screens/ranking_tab.dart                |   8 +-
 mobile/lib/screens/records_tab.dart                |  10 +-
 mobile/lib/screens/today_tab.dart                  |   2 +-
 mobile/lib/widgets/leaderboard_row.dart            |   6 +-
 mobile/lib/widgets/stat_bar.dart                   |   6 +-
 mobile/test/api/api_models_test.dart               |   6 +-
 mobile/test/api/dio_api_client_test.dart           |   4 +-
 mobile/test/fakes/fake_api_client.dart             |   4 +-
 .../test/golden/ranking_records_golden_test.dart   |  10 +-
 mobile/test/screens/ranking_tab_test.dart          | 115 ++++++++++++++++++++-
 mobile/test/screens/records_tab_test.dart          |  28 +++++
 mobile/test/widgets/result_sheet_test.dart         |  17 +++
 tests/test_hint_unlock.py                          |   2 +-
 tests/test_leaderboard.py                          |  40 +++++--
 tests/test_puzzle_language_api.py                  |   6 +-
 tests/test_ui_strings.py                           |  31 ++++++
 tests/test_web.py                                  |   6 +-
 tests/test_web_js.py                               |  56 ++++++++++
 web/static/app.js                                  |  23 ++++-
 27 files changed, 458 insertions(+), 77 deletions(-)
```

새 파일 4개(위 `--stat` 에는 안 나온다 — 아직 추적 전):

| 파일 | 무엇 |
|---|---|
| `tests/js/leaderboard_names.mjs` | ko/en 리더보드·분포 렌더 시나리오 |
| `review/web-detect-snapshots-38.py` | `impeccable detect` 스냅샷 생성 |
| `review/web-detect-rows-38.mjs` | 번들이 그린 행 마크업 추출 |
| `review/impl-evidence-38.md` | 이 문서 |

마이그레이션 변경 0건:

```
$ git diff --stat main -- migrations/
                                        # 비어 있음
$ uv run flask db heads
b1c7d4e0a932 (head)                     # 단일 head
```

## 6. 범위 · 안 한 것 · 남은 것

### 티켓 범위를 넘지 않으려고 한 것

- **복수형 범위는 코디네이터에게 묻고 정했다.** 조사해 보니 `1 tries` 계열 결함이
  `ranking.attempts` 하나가 아니라 7개 키였다(앱 4 + 웹 3). 티켓 문구가
  "`ranking.attempts`(및 같은 문제를 가진 키가 있으면 같이)" 라서 `orca orchestration
  ask` 로 "7개 전부 / 순위·통계 화면만 / 리더보드만" 셋을 물었고 **7개 전부**를
  받았다. `streak.days`·`streak.puzzles` 때문에 S1 홈·S4 내 기록 호출부도 건드렸지만
  **번역 JSON 과 `.tr()`→`.plural()` 호출부만**이고 화면 구조는 안 건드렸다.
- 제외한 키 4개(`attempts_left` 비율 표기, `fail_body` 의 고정 `max`, `{length}
  letters` 글자 수)는 README "38." 마지막 단락에 근거를 적었다.
- 리더보드 정렬·점수 인코딩·`me`(ZRANK) 경로·`is_me` 판정은 **한 줄도 안 바꿨다.**
- 서버가 UI 언어를 받게 하는 길(요청에 UI 언어를 더해 서버가 접두사를 고름)은 **안
  골랐다** — 응답을 캐시하거나 공유할 때 언어가 섞이고, 조회 하나에 언어 두 종류
  (UI·퍼즐)가 들어가서 읽기 어려워진다.

### 손대지 않은 공유 파일

`.env.example`(새 변수 없음), `docs/RELEASE.md`(사람이 할 절차 없음),
`docs/legal-checklist.md`, 법적 문서 템플릿(`web/templates/legal/privacy.en.html` 의
"The displayed name is an anonymous label derived from your guest number" 는 지금도
맞는 설명이다).

### 리뷰어가 볼 만한 것

- **`.scratch/store-launch/spec.md` 는 갱신하지 않았다.** 197·204행이 아직
  `display` 를 적고 있다. 스펙은 계획 단계의 산출물이고 이 티켓은 그 뒤에 들어온
  사용자 결정(2026-10-15)이라, 워커가 자기 번호 절만 덧붙이는 공유 파일 규칙에
  스펙이 안 들어 있어 건드리지 않았다. 갱신이 필요하면 코디네이터/Planner 몫이다.
- **`### 07.` 를 건드렸다.** 자기 번호 소제목만 덧붙이는 규칙의 예외다 — 07 의
  결론이 이 티켓과 정면으로 어긋나서 인용 블록 한 개를 덧붙였다(본문은 그대로).
  과하다고 보면 되돌리기 쉽다(블록 3줄).
- **배포 직후 열려 있던 탭의 `undefined`** — §2 의 "남는 위험". 하위 호환 필드를
  유지하는 쪽으로 판단이 뒤집히면 서버에 `display` 를 다시 더하고 웹·앱은 그대로
  두면 된다(클라이언트는 이미 `anon_tag` 만 읽는다).
