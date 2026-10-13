# 티켓 09 구현 증거 — 법적 문서 페이지 `/privacy`·`/terms` (ko/en) + 웹 디자인 토큰 CSS

브랜치 `dosaem/t09-legal-pages-token-css`, 로컬 `main`(`72a2a3c`) 위로 rebase 됨.

전용 테스트 자원(다른 워커와 겹치지 않게):

```sh
TEST_DATABASE_URL="mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t09?charset=utf8mb4"
TEST_REDIS_URL="redis://localhost:6379/11"
TEST_MIGRATION_DATABASE_URL="mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t09_migrations?charset=utf8mb4"
```

MySQL·Redis 는 이미 떠 있던 `chosung-daily-mysql-1`·`chosung-daily-redis-1` 을 그대로 썼고,
전용 DB 두 개만 새로 만들었다(공용 테스트 DB·Redis DB 는 건드리지 않음).

## 1. 무엇을 만들었나

| 파일 | 역할 |
|---|---|
| `web/static/tokens.css` (신규) | OVERRIDES 토큰 → CSS 변수. 라이트 `:root` + `prefers-color-scheme: dark`. **공용** — 15·16·18 이 재사용 |
| `web/static/legal.css` (신규) | 문서 페이지 레이아웃. 색·간격·폰트는 전부 tokens.css 변수 참조 |
| `web/templates/legal/_layout.html` (신규) | 공통 틀(head, 내비, 시행일, 푸터). 틀 문구만 언어별로 고름 |
| `web/templates/legal/privacy.{ko,en}.html` (신규) | 개인정보처리방침 본문 |
| `web/templates/legal/terms.{ko,en}.html` (신규) | 이용약관 본문 |
| `app/web.py` | `/privacy`·`/terms` 라우트, 시행일·연락처·EULA 링크 상수 |
| `app/utils/ui_language.py` (신규) | `?lang=` > Accept-Language > ko 판정 (순수 함수) |
| `tests/test_token_css.py` (신규) | 토큰이 OVERRIDES 표와 1:1인지, 그림자가 없는지 |
| `tests/test_legal_pages.py` (신규) | 렌더 200 + 두 언어 필수 공시 문구 |
| `tests/test_ui_language.py` (신규) | 언어 판정 12케이스 |
| `README.md` | "법적 문서" 절(경로표 + 갱신 책임), API 표 2행, "설계 판단" `### 09.` |

TDD 순서로 갔다 — 세 테스트 파일 모두 **먼저 실패시키고** 통과시켰다:
`ModuleNotFoundError: No module named 'app.utils.ui_language'` → 구현,
`FileNotFoundError: .../web/static/tokens.css` (51 errors) → 구현,
`ImportError: cannot import name 'LEGAL_CONTACT_EMAIL'` → 구현.

## 2. 체크박스별 증거

| # | 티켓 체크박스 | 무엇이 증명하나 | 결과 |
|---|---|---|---|
| 1 | OVERRIDES 토큰(배경·전경·brand·primary-button·tile-*·간격·폰트)을 CSS 변수로 옮긴 공용 스타일시트 1개 | `tests/test_token_css.py` — 색 토큰 14개 × (라이트/다크) 28케이스가 OVERRIDES §2 표 값과 문자열 일치 | 53 passed |
| 1 | `prefers-color-scheme` 다크 포함 | `test_dark_color_token_matches_overrides` (미디어 쿼리 안쪽만 떼어내 비교) + `test_declares_both_color_schemes` | passed |
| 1 | 그림자 없음 | `test_no_shadows` — `box-shadow`·`text-shadow` 문자열이 파일에 없음 | passed |
| 1 | Pretendard | `test_pretendard_is_the_primary_font` — `--font-sans` 첫 항목이 `pretendard variable`, Inter·system-ui 가 폴백 | passed |
| 1 | 기존 메인 페이지 스타일 안 건드림 | `test_main_page_style_is_untouched` + `git diff main..HEAD --stat` 에 `web/static/style.css`·`web/templates/index.html` 없음 | passed |
| 2 | `/privacy`·`/terms` Jinja 렌더, ko/en 본문 | `test_defaults_to_korean`, `test_accept_language_selects_english`, `test_lang_query_beats_accept_language`, `test_unknown_lang_falls_back` (각 2페이지) | passed |
| 2 | 수집 항목 6개 + 보유 기간 + 제3자·위탁 + 국외 이전 + 만 14세 미만 | `test_privacy_ko_covers_required_disclosures` (16문구) / `..._en_...` (16문구) | 32 passed |
| 2 | 삭제 방법(`/account/delete` 링크), 연락처(운영자 메일) | `test_privacy_links_deletion_page_and_contact` — 경로와 `mailto:` 둘 다 | passed (ko, en) |
| 3 | 구독 자동 갱신·해지(스토어에서) 안내 | `test_terms_ko_covers_subscription_rules` / `..._en_...` — `자동 갱신`/`automatically renew`, `해지`/`cancel`, `App Store`, `Google Play` | 10 passed |
| 3 | EULA 선택 자리(미정 9) | `test_terms_marks_eula_choice_as_pending` — Apple 표준 EULA URL 이 두 언어 모두에 있음 | passed (ko, en) |
| 4 | pytest 렌더 테스트(200, 두 언어 핵심 문구) | `tests/test_legal_pages.py` 전체 | 64 passed |
| 4 | 두 페이지에 `impeccable detect` 0건 (공용 토큰 CSS 기준) | 아래 §4 | ko/en × 2페이지 = **4 URL 모두 0건** |
| 5 | README 에 법적 문서 경로와 갱신 책임 메모 | `README.md` "법적 문서 (`/privacy`, `/terms`)" 절 — 경로표 + "갱신 책임은 운영자에게" + 갱신 트리거 5개 | 커밋 `3b0a364` |
| 5 | "설계 판단" 에 "웹 토큰 CSS 를 법적 페이지에서 먼저 도입" 한 줄 | `README.md` `### 09. 웹 디자인 토큰 CSS 를 법적 문서 페이지에서 먼저 도입` | 커밋 `3b0a364` |

## 3. 테스트·린트 실행 출력 (로컬 `main` 위로 rebase 한 뒤)

```
$ git rebase main
Current branch dosaem/t09-legal-pages-token-css is up to date.
```

(main 이 `72a2a3c` 에서 움직이지 않아 충돌 없음. `git log main..HEAD` 에 커밋 5개.)

```
$ uv run ruff check .
All checks passed!
exit=0

$ ./scripts/check_migration_heads.sh
4e72a4045fbc (head)
OK: Alembic head 1개
exit=0

$ uv run pytest -q
........................................................................ [ 22%]
........................................................................ [ 45%]
........................................................................ [ 68%]
........................................................................ [ 91%]
...........................                                              [100%]
315 passed in 140.15s (0:02:20)
exit=0
```

전체 315개 중 이 티켓이 추가한 것은 **129개**다(측정값):

```
$ uv run pytest tests/test_token_css.py tests/test_legal_pages.py tests/test_ui_language.py --collect-only -q
129 tests collected
    test_token_css.py    53
    test_legal_pages.py  64
    test_ui_language.py  12
```

마이그레이션은 만들지 않았다(템플릿·CSS·라우트만). 그래도 `flask db heads` 가 1줄인지
확인했다 — 위 출력대로 `4e72a4045fbc (head)` 하나다.

### 건너뛴 것 / 숨기지 않을 것

- **`ruff format --check .` 는 실패한다. 단, 내 파일 때문이 아니다.** 레포에 이미
  12개 파일이 `ruff format` 기준에 안 맞고(`app/models/account.py`,
  `app/utils/chosung.py`, `tests/test_migrations.py` 등), CI(`.github/workflows/ci.yml`)
  는 `ruff check` 만 돌린다 — 이 레포는 `ruff format` 을 게이트로 쓰지 않는다. 내가
  추가·수정한 5개 파일만 따로 돌리면 통과한다:
  ```
  $ uv run ruff format --check app/web.py app/utils/ui_language.py \
      tests/test_legal_pages.py tests/test_token_css.py tests/test_ui_language.py
  5 files already formatted
  ```
  레포 전체 포맷은 티켓 범위 밖이라 건드리지 않았다.
- **브라우저 스크린샷을 못 찍었다.** Chrome 확장으로 `127.0.0.1:5097`·`localhost:5097`
  둘 다 열어봤지만 `Error capturing screenshot: Frame with ID 0 is showing error page`
  로 3번 실패했다(서버는 같은 시점에 curl·detect 로 200 응답). 시각 확인은
  `impeccable detect`(아래, 실제로 페이지를 가져와 CSS 를 파싱한다)와 §5 의 구조
  검사로 대신했다 — 사람 눈으로 본 스크린샷은 이 증거에 없다.

## 4. `impeccable detect` — 0건 (+ 탐지기가 살아 있다는 대조군)

`detect` 는 Jinja 의 `url_for` 를 못 풀어서 템플릿 파일을 그냥 스캔하면 CSS 를 못 읽는다
(티켓 01 이 남긴 메모). 그래서 **개발 서버를 띄우고 URL 로** 돌렸다 — 이러면 detect 가
실제로 페이지를 받아 링크된 `tokens.css`·`legal.css` 를 파싱한다.

```
$ FLASK_ENV=testing uv run flask --app wsgi run --port 5097   # (백그라운드)

$ impeccable detect "http://127.0.0.1:5097/privacy?lang=ko"
exit=0

$ impeccable detect "http://127.0.0.1:5097/privacy?lang=en"
exit=0

$ impeccable detect "http://127.0.0.1:5097/terms?lang=ko"
exit=0

$ impeccable detect "http://127.0.0.1:5097/terms?lang=en"
exit=0
```

출력이 비고 exit=0 이면 findings 0건이다(티켓 01 증거와 같은 해석).

**"출력이 비었다" 가 "탐지기가 안 돌았다" 가 아님을 대조군 2개로 확인했다.**

대조군 1 — 폐기된 V2 목업(TOOLS.md 에 7건으로 기록돼 있는 파일), 파일 모드:

```
$ impeccable detect .scratch/store-launch/design/archive/v2_softdark_home.html
  [low-contrast] 2.8:1 (need 4.5:1) — text #f1f5f9 on #3fa66b     (×4)
  [low-contrast] 2.5:1 (need 4.5:1) — text #f1f5f9 on #f0795a
  [cramped-padding] <div> "flex": children flush against bg on all sides (no inset)
  [overused-font] Primary font: inter
7 anti-patterns found.
```

대조군 2 — **URL 모드가 링크된 CSS 를 실제로 읽는지**. 같은 서버의 `/static/` 에 일부러
위반한 페이지(초록 면 위 밝은 글자, 별도 CSS 파일)를 두고 URL 로 스캔:

```
$ impeccable detect "http://127.0.0.1:5097/static/_detect_control.html"
  [low-contrast] 2.8:1 (need 4.5:1) — text #f1f5f9 on #3fa66b
1 anti-pattern found.
```

→ URL 모드가 페이지를 받아 링크된 스타일시트를 파싱하고 규칙을 적용한다는 뜻이다.
대조군 파일 2개(`web/static/_detect_control.{html,css}`)는 확인 직후 삭제했고 커밋에 없다.

참고로 새 CSS 2개를 파일 모드로 돌려도 0건이다:

```
$ impeccable detect web/static/tokens.css web/static/legal.css
exit=0
```

`web/` 디렉터리 전체를 파일 모드로 돌리면 `url_for` 를 못 푸는 경고 3줄이 나오고 0건이다
(경고는 기존 `index.html` 과 새 `_layout.html` 의 Jinja 링크 때문 — 그래서 위 URL 모드가
이 티켓의 근거다).

## 5. 렌더된 HTML 구조 검사

탐지기가 안 보는 것(태그 균형, 안 치환된 Jinja, 헤딩 계층)을 따로 확인했다.

```
--- /privacy?lang=ko
  태그 균형 오류: 없음  / 안 닫힌 태그: 없음
  남은 Jinja 구문: 0
  헤딩: h1 1 / h2 9 / h3 0 → h1 하나 + h2 들 (정상)
--- /privacy?lang=en      (동일)
--- /terms?lang=ko
  헤딩: h1 1 / h2 10 / h3 0 → h1 하나 + h2 들 (정상)
--- /terms?lang=en        (동일)
```

h1 은 문서 제목 하나, 나머지는 h2 — SCREENS 의 목업 매핑표가 "h 태그 동일 크기 1건
(구현 시 시맨틱 헤딩으로 해결)" 으로 남긴 문제를 처음부터 피했다. h3 는 쓰지 않았다:
토큰 스케일(12/14/16/20/24/32)에서 h2(20px)와 본문(16px) 사이에 쓸 단계가 없어서,
단계를 더 만드는 대신 `dl`(항목/설명)로 구조를 냈다.

## 6. 디자인 판단 — DESIGN_DIR 과 다르게 한 것

목업이 **없는** 화면이다: 스펙 "디자인 부족 항목" 이 "웹 전체(`/account/delete` 포함) —
명세+토큰으로 구현, detect/critique 검증" 으로 지정하고 있고, SCREENS 의 목업 매핑표도
웹은 "목업 없음" 이다. 그래서 SCREENS "웹" 절 + OVERRIDES 토큰을 근거로 구현했다.

따른 것:

- **폭 480px**: SCREENS "웹" 절의 "`/privacy`, `/terms` 는 같은 레이아웃의 문서 페이지"
  + OVERRIDES §10(중앙 정렬 카드 하나, 481+ 에서 `max-width: 480px`). 긴 법적 문서에는
  좁지만, 디자인 문서가 명시한 규칙이라 그대로 뒀다(`--content-max-width`).
- **라이트 모드에 카드 면 없음**: OVERRIDES §4 "라이트 모드에서 카드도 없음 — 섹션
  구분은 헤어라인 1px 과 여백으로만". 그래서 `card` 토큰을 쓰지 않고 h2 위 `border-top`
  1px 로만 절을 나눴다.
- **brand 오렌지는 면·글자색 금지**: OVERRIDES §2. 링크 글자는 `foreground` 로 두고
  `text-decoration-color` 만 brand 로 줬다 — 라이트의 `#EA580C` on `#FAFAF9` 는 3.9:1 로
  AA 미달이라 글자색으로 쓸 수 없다. 포커스 링(`outline`)에도 brand 를 썼다(§2 허용).
- **그림자 없음**(§4), **Pretendard**(§3, CDN 버전 고정), **터치 타깃 44px**(§4 —
  내비·푸터 링크에 `min-height: var(--touch-target-min)`).

**다르게 한 것: 없음.** 디자인 문서에 답이 없어서 내가 정한 것은 아래 두 개다.

- `.doc-note`(미정 사항·백업 보존 안내를 담은 회색 블록)는 OVERRIDES 컴포넌트 목록(§6)에
  없는 요소다. 문서 페이지에만 필요한 보조 블록이라 `muted` 면 + `radius-card` 로
  기존 토큰만 조합했다 — 새 색이나 새 간격을 만들지 않았다.
- 헤딩 단계를 h1/h2 둘로만 썼다(§5 참고).

## 7. 스펙·티켓에 답이 없어 판단한 것

- **연락처 메일**: `hsseo@dosaem.com`. `CONTEXT.md` "운영자" 가 계정을 두 개로 못 박았고
  (`dosaem90@gmail.com`, `hsseo@dosaem.com`), 그중 Play 조직 계정을 썼다 — 스토어 콘솔·
  Play Data safety 양식이 가리킬 공개 연락처와 같아야 한다. 환경변수로 빼지 않고
  `app/web.py` 상수로 뒀다: 같은 문서가 "다른 메일 주소를 쓰지 않는다" 고 고정한
  프로젝트 사실이라 배포 환경마다 달라질 값이 아니다(`LEGAL_CONTACT_EMAIL`).
  이 판단과 서비스명·도메인(`chosung.dosaem.com`, "오늘의 초성 / Hidden Vowels",
  법인 정보 없는 개인 운영자 기준)은 `orca orchestration ask` 로 코디네이터에게
  물었으나(`msg_2a7bbb9a4266`) 답이 오지 않아, **위 근거로 진행했다.** 바꿀 거면
  상수 한 줄과 두 본문의 서비스명만 고치면 된다.
- **보유 기간의 구체값**: 스펙이 기간을 숫자로 주지 않아서, 레포에 실제로 있는 값만
  적었다 — 백업본 14일(`BACKUP_RETENTION_DAYS`, 티켓 21), 애플 revoke 재시도 7일
  (스펙 §A.7), 그 밖에는 "서비스 이용 중 보유, 계정 삭제 시 삭제". Sentry 는 보관
  기간을 숫자로 아는 근거가 없어 "Sentry 보관 정책에 따라 자동 삭제" 로 적었다.
- **백업본 14일을 방침에 썼다.** 삭제해도 그 이전 백업본에는 최대 14일 남는 게 사실이라
  숨기지 않았다. `BACKUP_RETENTION_DAYS` 를 바꾸면 방침의 14일도 고쳐야 한다 —
  README 갱신 트리거에 적어 뒀다.
- **광고 ID**: 스펙이 수집 항목으로 열거하지만 서버 컬럼이 없다. AdMob SDK 가 기기 광고
  ID 를 AdMob 으로 직접 보내고 **서버에는 저장하지 않는다** 로 적었다 — 사실과 다르게
  "우리가 수집한다" 고 쓰면 Data safety 양식과 어긋난다.

## 8. 범위 밖이라 하지 않은 것

- `/account/delete` 페이지는 **만들지 않았다**(티켓 14). 방침·푸터가 경로를 가리키기만
  한다 — Play Data safety 의 삭제 URL 이라 문서가 먼저 가리켜 둬야 한다. 지금 그 링크를
  누르면 404 다.
- 메인 페이지(`index.html`, `style.css`)를 토큰으로 옮기지 않았다(티켓 18).
- `.env.example`·`docs/RELEASE.md`·스펙 "미정 항목" 에 **덧붙인 행이 없다**: 새 환경변수를
  만들지 않았고, 릴리스 절차가 바뀌지 않았고, 미정 9(EULA)는 사람(D2)이 정할 항목이라
  티켓이 자기 번호 줄 추가를 지시하지 않았다.
- 레포 전체 `ruff format` 정리(§3 참고).

## 9. 남은 것

없음. 체크박스 5개 전부 테스트·명령 출력으로 증명됨.

후속 티켓이 알아야 할 메모:

- `web/static/tokens.css` 는 **변수만** 있다. 15·16·18 은 자기 페이지 스타일시트에서
  `var(--color-*)` 로 쓰면 되고, 토큰 값을 거기서 다시 정의하면 안 된다.
- `impeccable detect` 는 Jinja 템플릿 파일을 직접 스캔하면 CSS 를 못 읽는다. 15·16·18 도
  **개발 서버를 띄우고 URL 로** 돌려야 한다(§4 방식).
- UI 문구 ko/en 이 필요한 티켓(18)은 `app/utils/ui_language.py` 의
  `resolve_ui_language` 를 그대로 쓸 수 있다.

---

## 수정 라운드 1

`review/impl-review-09.md` 라운드 1(판정 FAIL, BLOCKER 0 / MAJOR 1 / MINOR 2)의 결함
3개를 전부 고쳤다. **틀렸다고 판단한 지적은 없다** — 세 건 다 리뷰의 재현 방법대로
먼저 재현됐다. 코디네이터가 추가로 지시한 사용자 결정 2건(`msg_386a4e947738`)도 이
라운드에 함께 넣었다(§수정 라운드 1 — 사용자 결정 반영).

각 결함은 **재현 → 실패하는 테스트로 고정 → 고침** 순서로 처리했다.

### D-09-1 (MAJOR) — 게스트 플레이를 국외 이전 거부 방법으로 잘못 안내

**재현.** `/privacy?lang=ko`·`?lang=en` 4절 마지막 문장이 "계정을 연결하지 않고
게스트로만 플레이하면 (국외 이전을) 피할 수 있다" 였다. 같은 방침 1절·3절은 AdMob SDK
가 광고 ID 를 **직접** 보내고 Firebase Analytics·Sentry 가 이벤트·오류를 처리한다고
적고 있다. 스펙과 대조한 결과도 같다 — §B.21 광고 게이트의 조건은 UMP
`canRequestAds`/ATT 상태이지 계정 연결 여부가 아니고(`spec.md:210`), §B.24 분석 이벤트
4개와 §C.30 Sentry 어디에도 "연결된 계정만" 조건이 없다. 즉 게스트로 플레이해도
광고·분석·오류 전송은 그대로 일어난다.

**원인.** 거부 수단을 기능별로 나누지 않고 "계정 연결" 하나로 묶어 쓴 문구 오류다.
계정 연결로 실제로 막히는 것은 로그인 제공자(Google/Apple)로 가는 식별자·이메일이고,
구독을 안 쓰면 스토어로 가는 구매 식별자가 막힌다 — 그 둘만 사실이었다.

**수정.** 4절을 기능별 거부 방법으로 다시 썼다(ko/en 같은 구조).

- 계정 미연결 → 로그인 제공자 이전 없음, 구독 미사용 → 스토어 이전 없음 (사실만 남김)
- **"계정을 연결하지 않아도 앱의 광고·앱 사용 이벤트·오류 기록은 그대로 전송됩니다"**
  를 명시하고 "게스트로 쓰는 것은 국외 이전을 거부하는 방법이 아닙니다" 로 못 박음
- 광고(AdMob): iOS 추적 허용 요청 + 앱 "광고 개인정보 설정"(표시되는 지역)에서 맞춤
  광고를 거부·재선택할 수 있고, **거부해도 광고 요청 자체는 AdMob 으로 간다**, 전송을
  없애려면 구독 또는 앱 삭제
- 앱 사용 이벤트(Firebase Analytics): 앱에서만, **개별 거부 수단 없음**
- 오류 기록(Sentry): 웹·앱 모두, 장애 대응에 필요해 **개별 거부 수단 없음**
- 받아들일 수 없으면 이용 중단 + 6절 삭제 안내

**증명하는 테스트.** `tests/test_legal_pages.py` 에 4절 본문만 떼어 검사하는 절을
추가했다(같은 단어가 다른 절에 있어도 통과하지 않게 `<h2>4.`~`<h2>5.` 사이만 본다).

| 테스트 | 무엇을 막는지 |
|---|---|
| `test_transfer_section_is_the_international_transfer_section` | 헬퍼가 엉뚱한 절을 떼어 와서 아래 두 테스트가 공짜로 통과하는 것 |
| `test_transfer_section_does_not_sell_guest_play_as_opt_out` | "게스트로만 플레이"/"play as a guest without linking" 문구의 재발 |
| `test_transfer_section_ko_states_real_opt_outs` (5건) | 계정을 연결하지 않아도 / 광고 개인정보 설정 / 추적 허용 / 개별 거부 수단 / 구독 |
| `test_transfer_section_en_states_real_opt_outs` (5건) | even without a linked account / ad privacy settings / tracking permission / no per-feature opt-out / subscription |

수정 전 이 테스트들이 **빨갛게 떨어지는 것**을 먼저 확인했다(아래 §재현 로그).

### D-09-2 (MINOR) — 지역 언어 태그가 있으면 낮은 q 값의 언어를 선택

**재현.** 리뷰의 curl 과 같은 조합을 개발 서버(loopback `127.0.0.1:5099`)에 보냈다.

```
$ curl -s -D - -o /dev/null -H 'Accept-Language: en-US,ko;q=0.1' http://127.0.0.1:5099/privacy | grep -i '^content-language'
Content-Language: ko      # ← 기대: en
$ curl -s -D - -o /dev/null -H 'Accept-Language: ko-KR,en;q=0.1' http://127.0.0.1:5099/privacy | grep -i '^content-language'
Content-Language: en      # ← 기대: ko
```

순수 함수로도 같았다: `resolve_ui_language(None, 'en-US,ko;q=0.1') == 'ko'`.

**원인(코드로 확인).** 설치된 werkzeug 3.1.9 의 `LanguageAccept.best_match` 소스를
직접 읽었다 — `super().best_match(matches)` 로 **완전 일치를 먼저** 찾고, 그게 None 일
때만 주 언어(primary subtag)로 내려간다. 그래서 `en-US`(q=1)는 1차 통과에서 지원 목록
`("ko", "en")` 과 완전 일치하지 않고, 같은 1차 통과에서 `ko`(q=0.1)가 완전 일치로
잡혀 버린다. q 값 비교가 "완전 일치끼리" 안에서만 일어나는 구조라, 지역 꼬리표가 붙은
선호 언어는 항상 뒤로 밀린다. 증상(언어가 뒤바뀜)이 아니라 이 선택 순서를 고쳤다.

**수정.** `app/utils/ui_language.py` 가 `best_match` 를 쓰지 않고, 파싱(q 값 해석·정렬)
만 werkzeug 에 맡긴 뒤 **꼬리표를 먼저 떼고 선호 순서대로** 지원 언어를 찾는다
(`_accepted_languages`). werkzeug 의 `Accept` 순회 순서는 q 내림차순이고 q 가 같으면
헤더에 적힌 순서라는 것을 소스(`Accept.__init__` 의 `sorted(..., reverse=True)`)와
실제 출력으로 확인했다. `q=0`("받지 않겠다")은 버린다.

**증명하는 테스트.**

- `tests/test_ui_language.py::test_resolve_ui_language` 에 8케이스 추가:
  `en-US,ko;q=0.1`→en, `ko-KR,en;q=0.1`→ko, `en-GB,ko;q=0.5`→en, `ko_KR,en;q=0.5`→ko,
  `en;q=0,ko;q=0.5`→ko, `ko;q=0,en;q=0.3`→en, `ko;q=0`→ko(기본값), `*`→ko(기본값)
- `tests/test_legal_pages.py::test_region_tag_does_not_lose_to_low_q_language`
  (4케이스): HTTP 수준에서 `Content-Language` 와 `<html lang=...>` 를 같이 확인

수정 후 같은 curl:

```
$ curl ... -H 'Accept-Language: en-US,ko;q=0.1' .../privacy  → Content-Language: en
$ curl ... -H 'Accept-Language: ko-KR,en;q=0.1' .../privacy  → Content-Language: ko
```

### D-09-3 (MINOR) — 문서 외곽 폭과 모바일 패딩이 디자인 규칙을 벗어남

**재현(실제 브라우저).** 리뷰와 같은 값을 측정했다. 이 세션에서도 Chrome 확장은
`127.0.0.1`·`localhost` 둘 다 `chrome-error://chromewebdata/` 로 떨어져서(구현 라운드와
같은 증상), **헤드리스 Chrome** 으로 쟀다. 재현 스크립트를 커밋에 넣었다:
`review/measure-doc-width-09.py` (개발 서버의 렌더 HTML + 실제 `tokens.css`·`legal.css`
inline → 폭 고정 iframe 안에서 열어 computed style 읽기. iframe 을 쓴 이유는 macOS
헤드리스 Chrome 의 창 폭 하한이 500px 이라 ≤480 미디어 쿼리를 창 크기로 못 만든다).

수정 전 (4 URL 모두 동일):

```
privacy-ko @768px {"docOuterWidth": 528, "boxSizing": "content-box", "paddingLeft": "24px", "maxWidth": "480px"}
privacy-ko @375px {"docOuterWidth": 375, "boxSizing": "content-box", "paddingLeft": "24px"}
```

**원인.** `.doc` 가 기본 `box-sizing: content-box` 였다. CSS 의 `max-width` 는
content-box 기준이라 좌우 패딩 24px 이 밖으로 더해져 외곽 폭이 528px 이 된다 —
OVERRIDES §10 의 "카드 `max-width: 480px`" 은 카드 **외곽** 폭이다. 패딩 24px 는
§4 의 "카드 패딩 16(모바일) 24(태블릿+)" 중 태블릿 값만 모든 폭에 쓴 것이다.

**수정.** `web/static/legal.css`

```css
.doc { box-sizing: border-box; max-width: var(--content-max-width); margin: 0 auto;
       padding: var(--space-4) var(--space-4) var(--space-12); }
@media (min-width: 481px) { .doc { padding: var(--space-6) var(--space-6) var(--space-12); } }
```

경계를 481px 로 둔 근거: OVERRIDES §10 이 "≤480 폭 100% / 481+ 카드 480px" 로 같은
지점을 쓰고 있어서, 폭이 고정되는 지점과 패딩이 넓어지는 지점을 다르게 둘 이유가 없다.
새 색·새 간격 토큰은 만들지 않았다(기존 `--space-4`/`--space-6`).

수정 후 (4 URL × 3 폭 전부):

```
@375px {"viewport":375,"docOuterWidth":375,"boxSizing":"border-box","paddingTop":"16px","paddingLeft":"16px","paddingRight":"16px","maxWidth":"480px","horizontalOverflow":false}
@481px {"viewport":481,"docOuterWidth":480,"boxSizing":"border-box","paddingTop":"24px","paddingLeft":"24px","paddingRight":"24px","maxWidth":"480px","horizontalOverflow":false}
@768px {"viewport":768,"docOuterWidth":480,"boxSizing":"border-box","paddingTop":"24px","paddingLeft":"24px","paddingRight":"24px","maxWidth":"480px","horizontalOverflow":false}
```

**증명하는 테스트.** `tests/test_legal_css.py` (새 파일). 레포에 브라우저 드라이버
의존성이 없어서(테스트 때문에 의존성을 늘리지 않는다) px 를 만드는 CSS 선언을 고정한다.
`.doc` 블록을 떼어 `box-sizing: border-box`·`max-width: var(--content-max-width)`,
기본 padding 이 `--space-4`(그리고 `--space-6` 이 아님), `min-width: 481px` 블록의
padding 이 `--space-6` 임을 확인한다. 색 리터럴·그림자가 없다는 것도 같이 고정했다.

**리뷰의 증거 문서 지적도 정정한다.** 이 문서 §6 의 "**다르게 한 것: 없음**" 과
"폭 480px" 은 당시 구현 상태(외곽 528px·패딩 24px 고정)와 맞지 않는 주장이었다. 이제
실측이 480px/16·24px 라 §6 의 주장이 사실과 일치한다.

### 수정 라운드 1 — 사용자 결정 반영 (코디네이터 추가 지시)

리뷰 결함이 아니라, 구현 라운드의 `ask`(`msg_2a7bbb9a4266`)가 답을 못 받고 끝난 항목에
대한 사용자 결정이다(`msg_386a4e947738`).

**(1) 공개 연락처를 설정값으로.** `app/web.py` 의 모듈 상수를 지우고
`app/config.py` 의 `LEGAL_CONTACT_EMAIL`(기본값 `hsseo@dosaem.com`)로 옮겼다. 주소
자체는 사용자 확인대로 그대로다. `.env.example` 에 `# [09]` 절을 파일 끝에 추가.

기본값을 `os.environ.get(...) or "hsseo@dosaem.com"` 로 쓴 이유: `.env.example` 을
복사해 쓰면 `LEGAL_CONTACT_EMAIL=` 이 **빈 문자열로 환경에 들어와서**
`os.environ.get(key, default)` 가 기본값으로 안 떨어진다. 문서의 연락처가 비면 스토어
심사 반려 사유라 `or` 로 막았고, 그 동작을 테스트로 고정했다
(`test_empty_contact_email_env_falls_back_to_the_default`).

**(2) 운영자 정보(사업자 정보) 블록.** 설정값 5개를 만들고 기본값은 전부 빈 문자열이다 —
**실제 값은 지어내지 않았다.**

| 설정 | 문서 라벨 (ko / en) |
|---|---|
| `LEGAL_BUSINESS_NAME` | 상호 / Business name |
| `LEGAL_REPRESENTATIVE` | 대표자 / Representative |
| `LEGAL_BUSINESS_REG_NO` | 사업자등록번호 / Business registration number |
| `LEGAL_MAIL_ORDER_REG_NO` | 통신판매업 신고번호 / Mail-order business registration no. |
| `LEGAL_BUSINESS_ADDRESS` | 주소 / Address |

렌더는 `web/templates/legal/_layout.html` 의 `.doc-operator` 블록 하나로 두 문서가
같이 쓴다(사업자 등록 뒤 한 곳만 고치면 된다). `app/web.py` 의 `_business_info()` 가
**값이 있는 항목만** (라벨, 값) 으로 넘기므로, 전부 비면 서비스명(`오늘의 초성 /
Hidden Vowels (chosung.dosaem.com)`)과 연락처만 나온다. 라벨 순서는 전자상거래법 표기
순서. `.doc-operator` 는 `.doc` 안쪽이라 기존 `.doc h2`/`.doc dl` 규칙을 그대로 받고,
새 CSS·새 토큰을 만들지 않았다.

테스트(`tests/test_legal_pages.py`, 두 문서 × 두 언어):

- `test_operator_block_shows_service_and_contact` — 블록 제목·도메인·`mailto:` 존재
- `test_unset_business_info_is_not_rendered` — 기본(전부 빈 값)에서 `<dt>상호</dt>`
  같은 빈 줄이 **생기지 않음**
- `test_set_business_info_is_rendered` — 5개를 채우면 라벨·값이 전부 나옴
- `test_partially_set_business_info_renders_only_filled_rows` — 사업자 등록만 끝난
  중간 상태에서 채운 3줄만 나오고 통신판매업·주소는 안 나옴
- `test_business_info_values_are_not_hardcoded` — `app/config.py` 의 5개 기본값이
  모두 `""` 인지 (코드에 지어 넣은 상호·등록번호가 없다는 보증)

문서 갱신: `docs/RELEASE.md` 에 `### 09. 법적 문서 — 출시 전 사람이 채울 값` 절(환경변수
↔ 라벨 표 + 체크리스트 3개), README "법적 문서" 표의 연락처 행을 설정값으로 고치고
갱신 트리거에 "사업자·통신판매업 등록이 끝났을 때" 한 줄 추가. 스펙 "미정 항목" 과
마이그레이션은 건드리지 않았다(이 변경에 DB 가 없다).

사업자 정보를 채운 상태에서도 `impeccable detect` 는 0건이다:

```
$ FLASK_ENV=testing LEGAL_BUSINESS_NAME=... LEGAL_REPRESENTATIVE=... \
    LEGAL_BUSINESS_REG_NO=... LEGAL_MAIL_ORDER_REG_NO=... LEGAL_BUSINESS_ADDRESS=... \
    uv run flask --app wsgi run --port 5099       # (백그라운드)
$ impeccable detect "http://127.0.0.1:5099/privacy?lang=ko"   → exit=0
$ impeccable detect "http://127.0.0.1:5099/terms?lang=en"     → exit=0
```

### 재현 로그 — 수정 전 빨강 → 수정 후 초록

수정 전(테스트만 추가한 상태):

```
21 failed, 85 passed in 51.42s

FAILED tests/test_ui_language.py::test_resolve_ui_language[None-en-US,ko;q=0.1-en]
FAILED tests/test_ui_language.py::test_resolve_ui_language[None-ko-KR,en;q=0.1-ko]
FAILED tests/test_ui_language.py::test_resolve_ui_language[None-en-GB,ko;q=0.5-en]
FAILED tests/test_ui_language.py::test_resolve_ui_language[None-ko_KR,en;q=0.5-ko]
FAILED tests/test_legal_css.py::test_doc_card_width_counts_padding
FAILED tests/test_legal_css.py::test_doc_mobile_padding_is_16px
FAILED tests/test_legal_css.py::test_doc_tablet_padding_is_24px
FAILED tests/test_legal_pages.py::test_region_tag_does_not_lose_to_low_q_language[...] (4건)
FAILED tests/test_legal_pages.py::test_transfer_section_does_not_sell_guest_play_as_opt_out[ko-...]
FAILED tests/test_legal_pages.py::test_transfer_section_does_not_sell_guest_play_as_opt_out[en-...]
FAILED tests/test_legal_pages.py::test_transfer_section_ko_states_real_opt_outs[...] (4건)
FAILED tests/test_legal_pages.py::test_transfer_section_en_states_real_opt_outs[...] (4건)
```

### 전체 재검증 (로컬 main `8115301` 위로 rebase 후)

접속값은 이 문서 머리의 로컬 테스트 설정과 같다(DB `chosung_daily_test_t09`, Redis
DB 11). 공용 테스트 DB 는 건드리지 않았고, 이 문서에 인증값을 새로 적지 않는다.
`git diff main...HEAD --check` exit 0, 작업 트리 clean.

```
$ uv run pytest -q
536 passed in 232.97s (0:03:52)        # 환경 오류 0건

$ uv run ruff check .
All checks passed!

$ uv run ruff format --check app/web.py app/config.py app/utils/ui_language.py \
    tests/test_legal_pages.py tests/test_token_css.py tests/test_ui_language.py \
    tests/test_legal_css.py review/measure-doc-width-09.py
8 files already formatted

$ FLASK_ENV=testing uv run flask --app wsgi db heads
ff06a1bf5afc (head)          # 1줄. 이 티켓은 마이그레이션을 만들지 않는다 —
                             # 이 리비전은 rebase 로 들어온 main 의 것이다.

$ impeccable detect "http://127.0.0.1:5099/{privacy,terms}?lang={ko,en}"
4 URL 전부 exit=0            # 대조군 v2_softdark_home.html 은 7건/exit=2 (탐지기 생존)

$ curl -H 'Accept-Language: en-US,ko;q=0.1' .../privacy  → Content-Language: en
$ curl -H 'Accept-Language: ko-KR,en;q=0.1' .../privacy  → Content-Language: ko
```

레포 전체 `ruff format --check .` 는 이 문서 §3 에 적은 대로 **내 파일이 아닌** 기존
12개 파일 때문에 여전히 실패한다(CI 게이트는 `ruff check` 뿐). 그래서 이 라운드에서
건드린 8개 파일만 따로 확인했다.

### 미수정 MINOR

없음. 라운드 1 의 MINOR 2건(D-09-2, D-09-3) 모두 고쳤다.

리뷰의 "보안·범위·테스트 품질 및 참고" 에 적힌 검증 강도 두 가지는 리뷰 자신이 "별도
출시 차단 결함으로 중복 집계하지 않는다" 고 적은 항목이라 결함으로 세지 않았고, 이
라운드에서 **고치지 않았다**:

- `test_privacy_states_backup_retention` 의 느슨한 `"14"` 검사 — 본문에 "만 14세" 와
  "백업 14일" 이 둘 다 필수 공시로 들어 있어서 숫자 하나로는 구분이 안 된다. 제대로
  고치려면 두 문구를 각각 검사하도록 이 테스트를 쪼개야 한다.
- 토큰 테스트가 OVERRIDES 파일 자체가 아니라 복사한 기대값을 비교하는 점 — 고치려면
  `tests/test_token_css.py` 가 OVERRIDES 의 표를 파싱하게 바꿔야 한다.

둘 다 결함 수정 범위를 넘는 테스트 리팩토링이라 다음 티켓/라운드 몫으로 남겨 둔다.
