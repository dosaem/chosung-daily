# 티켓 16 구현 증거 — 법적 문서 법 기준 보완 · `docs/legal-checklist.md`

- 브랜치: `dosaem/t16-legal-compliance-checklist` (로컬 `main` = `4d83feb` 티켓 13 머지 위로 rebase)
- 커밋 3개(+ 이 문서): `test(16)` 체크리스트·테스트(red) → `feat(16)` 본문·조각·설정(green) → `docs(16)` README·RELEASE·스펙
- 마이그레이션 없음(DB 변경이 없는 티켓). 그래도 `flask db heads` 를 확인했다 — §5
- 전용 자원: DB `chosung_daily_test_t16`, Redis DB 4, 마이그레이션 DB `chosung_daily_test_t16_migrations`
- NAS(`~/SynologyDrive/.../business-info.md`)는 **열지 않았다** — 디스패치 제약이 NAS 접속을 금지하고,
  사업자 정보 값은 레포가 아니라 사람이 prod `.env` 에 넣는 구조라 값이 필요하지 않았다. 코드·문서에는
  설정 키 이름만 있다

## 1. 사용자 확인 3건 (티켓 "사용자 확인 필요", 스펙 미정 21)

체크리스트 초안을 먼저 쓴 뒤 `orca orchestration ask` **한 번**으로 세 질문을 묶어 보냈고, 각 항목에
법적 근거(어느 조문이 표시를 요구하는지, 통신판매업 신고 대상이면 달라지는 점)를 한 줄씩 붙였다.
받은 답(2026-10-14):

| 질문 | 답 | 구현 |
|---|---|---|
| 1. 사업장 주소(자택) 공개 범위 | **(b)** 시·구까지만 + "상세 주소는 요청 시 이메일로 제공". 축약 값은 `.env` 로 받고 코드가 자르지 않으며 기본값은 비움 | `LEGAL_BUSINESS_ADDRESS`(기본 `""`). 값이 있을 때만 조각이 안내 문구를 함께 렌더(`web/templates/legal/_business_info.html`) |
| 2. 공개용 전화번호 | **(b)** 설정값, 비면 미표시 | `LEGAL_BUSINESS_PHONE` 추가(`app/config.py`, `LEGAL_BUSINESS_FIELDS`) |
| 3. 보호책임자 표기 | **(b)** 직책 "운영자" + 이메일. 성명은 `.env` 를 채우면 표시 | `privacy#officer` + `LEGAL_PRIVACY_OFFICER`(비면 직책만) |

답을 받기 전 구현은 세 항목 모두 "미표시"(설정값 비움)였고, 받은 답이 그 기본 상태와 같아서 되돌린
코드는 없다. 추가 요구사항도 반영했다: 축약 주소의 적법성과 "운영자가 전상법 §13 의 통신판매업자인지"
는 전문가 확인 항목으로 `docs/RELEASE.md` "### 16." 과 스펙 미정 21 에 적었고, 세 답은
`docs/legal-checklist.md` 의 해당 조문 행에 "사용자 결정(2026-10-14)" 으로 들어갔다.

## 2. 체크박스별 근거

| 티켓 체크박스 | 무엇이 이걸 증명하는가 |
|---|---|
| `docs/legal-checklist.md`: "근거(조문) → 요구 내용 → 문서·절 id → 확인 테스트" 표를 개보법 §30①·시행령 §31 전 항목, §29, §31, §22의2, 방침 변경에 대해 쓴다 | `docs/legal-checklist.md` §1(16행). 파싱 가능성과 "모든 행이 절 id·확인 테스트를 갖는지" 는 `tests/test_legal_checklist.py::test_the_clause_tables_are_parseable`(조문 행 ≥30 — 실측 46행), `::test_every_clause_row_points_at_a_document_section` |
| 제28조의8 ② 국외 이전 고지 — Google·Apple·AdMob·Firebase·Sentry **각각 한 행**, 받는 자 연락처는 각사 공개 문서 URL 만(추정 금지) | 체크리스트 §2(7행) + 본문 `privacy#overseas` 의 수탁자 5개 × 5칸(이전 항목 / 국가·시기·방법 / 받는 자·연락처 / 목적·보유 기간 / 거부 방법·효과). 테스트 `::test_overseas_section_lists_every_recipient[ko|en-{Google,Apple,AdMob,Firebase,Sentry}]` 이 **이름과 그 회사가 공개한 URL 을 짝으로** 확인(10 케이스). 연락처는 `policies.google.com/privacy`, `apple.com/legal/privacy`, `policies.google.com/technologies/ads`, `firebase.google.com/support/privacy`, `sentry.io/privacy` 뿐 — 개인 담당자 주소를 지어내지 않았다 |
| 전상법 §10(신원·이용약관·호스팅)·§13(신고번호·청약철회·환불 주체)·§17②(디지털콘텐츠 철회 제한) | 체크리스트 §3(13행) + `terms#business-info`(조각), `terms#withdrawal`, `terms#subscription`. 테스트 `::test_terms_ko_has_the_required_phrases[청약철회|환불|디지털 콘텐츠|호스팅|자동 갱신|해지|App Store|Google Play]`, en 은 `[withdraw|refund|digital content|hosting|auto-renew|cancel|...]`. 신고번호가 비면 행이 없는 것은 `tests/test_legal_pages.py::test_partially_set_business_info_renders_only_filled_rows` |
| Apple 3.1.2(a)·Google Play 구독 고지 | 체크리스트 §4(6행) + `terms#subscription` 의 상품 이름·가격·구독 기간·결제 주기·자동 갱신(24시간 전 해지)·해지 경로(설정 > Apple 계정 > 구독 / Google Play > 구독)·복원. 테스트는 위 문구 표와 `tests/test_legal_pages.py::test_terms_{ko,en}_covers_subscription_rules` |
| Apple 표준 EULA 사용 여부(미정 9) 결정·근거 한 줄 | 체크리스트 §4 의 EULA 행 + `terms#eula` 의 `doc-note`("표준 EULA 를 그대로 쓴다 — 표준과 달리 정할 조건이 없고 ASC 에 별도 입력이 필요 없다"). 링크 고정은 `tests/test_legal_pages.py::test_terms_marks_eula_choice_as_pending`. 스펙 미정 9·README 갱신 트리거·RELEASE "### 16." ASC 항목에 같은 결정 |
| 해외 사용자 최소 고지 포함 여부 결정·근거(미정 23) | 체크리스트 §5(결정: 포함 + 근거 4행) + `privacy#international-users`(EU·영국: 법적 근거 Art.6(1)(b)(f), 권리 Art.15~21, 감독기관 민원 Art.77 / 캘리포니아: 판매·공유 안 함, 열람·삭제·정정, 차별 금지). 테스트 `::test_privacy_ko_has_the_required_phrases[법적 근거]`, `::test_privacy_en_has_the_required_phrases[supervisory authority]`, `[do not sell]`, `[legal basis]` |
| ko/en 본문 보완: 체크리스트의 모든 행이 두 언어에 같은 `id` 의 절로, 절 구조·순서 동일 | `::test_every_checklist_section_id_exists_in_both_languages`(28개 절 참조 × ko/en = 56 케이스), `::test_rendered_section_ids_are_all_in_the_checklist`(본문에만 있는 절도 실패 — 양방향), `::test_section_ids_match_in_order_across_languages`(ko·en `<h2 id=>` 순서 리스트가 같고 중복 없음) |
| 작성지침 권장 구성으로 재배열 | 방침 절 순서: `general` → `purposes` → `collection` → `third-parties` → `processors` → `overseas` → `destruction` → `rights` → `security` → `automatic-collection` → `children` → `officer` → `remedies` → `international-users` → `changes` → `business-info`(체크리스트 §7 에 목록). 재배열로 절 번호가 바뀌었으므로 `tests/test_legal_pages.py` 의 `_international_transfer_section` 을 번호 대신 `id="overseas"` 로 고쳤다 |
| 보유 기간 숫자가 현행 구현 값과 일치 | 백업 **14일** = `docker-compose.prod.yml` `BACKUP_RETENTION_DAYS: 14`·`scripts/backup.sh` 기본값, 애플 revoke 재시도 **7일** = `app/services/apple_revocation_service.py` `RETRY_MAX_AGE = timedelta(days=7)`, 계정 삭제 즉시 = `app/services/account_deletion_service.py` 한 커밋. 테스트 `::test_privacy_ko_has_the_required_phrases[14일]`,`[7일]`, en `[14 days]`,`[7 days]`, `tests/test_legal_pages.py::test_privacy_states_backup_retention` |
| 기존 `tests/test_legal_pages.py` 가 깨지지 않거나 같은 커밋에서 수정 | 같은 커밋(`feat(16)`)에서 2곳 수정: ① `_international_transfer_section` 을 id 기반으로 ② 운영자 정보 라벨 목록에 전화번호 추가·필드 순서 변경·`test_business_info_values_are_not_hardcoded` 에 새 키 2개 추가. 나머지 테스트는 그대로 통과(§3) |
| 사업자 정보는 **설정값으로만**(코드 기본값 없음), `LEGAL_BUSINESS_PHONE` 추가, 주소는 코드가 자르지 않음, 레포에 상호·등록번호·주소 없음 | `app/config.py` 의 `os.environ.get("LEGAL_*", "")` 7개 — `tests/test_legal_pages.py::test_business_info_values_are_not_hardcoded`(새 키 포함). 레포 전체 부재는 `tests/test_legal_checklist.py::test_repo_has_no_business_registration_number`(`web/templates`·`app`·`docs`·`README.md`·`.env.example` 에서 `\d{3}-\d{2}-\d{5}` 탐색 — 테스트 파일은 더미 번호를 쓰므로 제외). 자르는 코드 없음: `_business_info()` 는 `.strip()` 만 한다 |
| 사업자 정보 블록을 Jinja 조각으로 분리, `/terms` 하단·`/privacy` 책임자 절이 같은 조각, 18 의 푸터는 include 만, 신고번호 비면 그 행 없음 | `web/templates/legal/_business_info.html`(새 파일, `id="business-info"`), `privacy.{ko,en}.html`·`terms.{ko,en}.html` 끝의 `{% include %}`, `_layout.html` 에서 블록 제거. 두 문서 모두에서 렌더되는지 `tests/test_legal_pages.py::test_operator_block_shows_service_and_contact[privacy|terms × ko|en]`, 빈 값 미표시 `::test_unset_business_info_is_not_rendered`, 채운 값 표시 `::test_set_business_info_is_rendered`, 부분 상태 `::test_partially_set_business_info_renders_only_filled_rows` |
| 테스트 ① 절 id 양쪽 존재 ② ko·en 집합·순서 동일 ③ 핵심 문구 ④ `/account/delete` 링크 + 삭제 항목 ⊆ 방침 처리 항목 | ① `::test_every_checklist_section_id_exists_in_both_languages` ② `::test_section_ids_match_in_order_across_languages` ③ `::test_privacy_{ko,en}_has_the_required_phrases`(15/17개), `::test_terms_{ko,en}_has_the_required_phrases`(8/8개) — 보유 기간 숫자·자동 갱신/auto-renew·해지 경로·환불 주체·118·1833-6972·보호책임자·만 14세·광고 ID 초기화·국외 이전 거부·청약철회 ④ `::test_delete_page_is_linked_from_the_rights_section`(권리 절 안에 `/account/delete?lang=..`), `::test_deleted_data_names_are_a_subset_of_the_policy_items[ko|en]`(세션을 심어 확인 폼의 `<dt>` 집합 ⊆ 방침 `#collection` 의 `<dt>` 집합) |
| `impeccable detect` 0건(`/privacy`·`/terms` 두 언어, 문구를 바꾼 `/account/delete` 포함) | §4 — URL 8개 + CSS 2개 모두 0건, 대조군 7건으로 탐지기 생존 확인 |
| `LEGAL_EFFECTIVE_DATE` 갱신 | `app/web.py` 의 값이 이미 **2026-10-14**(티켓 09 가 같은 날 넣었고 이 작업도 같은 날이다) — 올릴 날짜가 없어 **바꾸지 않았다**. 숨기지 않고 적는다. `tests/test_legal_pages.py::test_shows_effective_date` 는 그대로 통과 |
| README "법적 문서" 절에 체크리스트 링크·갱신 트리거, "설계 판단" `### 16.` | `README.md:147~` 표에 조각·체크리스트 행 2개와 "관련 법·스토어 정책이 개정될 때" 트리거, `README.md:1391` `### 16. 법적 문서 — 사업자 정보는 설정값으로만, 공개 범위는 사람이 정한다` |
| `docs/RELEASE.md` "### 16." 사람 확인 체크박스 + 사용자 확인 결과 3건 | `docs/RELEASE.md` 끝 — 결과 표 3행 + 체크박스 8개(통신판매업 신고, 축약 주소 적법성, 보호책임자 지정, 전문가 검토, ASC EULA, Play Data safety 대조, 스토어 구독 고지 일치, 값 반영 후 눈 확인) |
| 스펙 미정 9·21·22·23 에 결과 기록, §A.15 항목 목록은 건드리지 않음 | `.scratch/store-launch/spec.md` "미정 항목" 섹션 끝에 `- (티켓 16 반영) 미정 9·21·22·23 결과: …` 한 줄 추가(자기 행만). §A.15 본문 diff 없음 — `git diff main..HEAD -- .scratch/store-launch/spec.md` 가 1줄 추가뿐 |
| 분할선 | **쓰지 않았다** — 해외 사용자 절(미정 23)과 스토어 구독 고지 행(Apple 3.1.2(a)·Play)까지 이 티켓에서 다 했다. 코디네이터에게 알릴 분할 없음 |

## 3. 테스트·린트 실행

모든 실행에 공통(전용 자원):

```
TEST_DATABASE_URL="mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t16?charset=utf8mb4"
TEST_REDIS_URL="redis://localhost:6379/4"
TEST_MIGRATION_DATABASE_URL="mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t16_migrations?charset=utf8mb4"
```

### 3.1 red → green (tdd)

테스트를 먼저 쓰고 돌려서 실패를 봤다(본문 재배열 전):

```
$ uv run pytest tests/test_legal_checklist.py -q
...
82 failed, 35 passed in 142.18s (0:02:22)
(exit=0 — tail 로 받은 출력)
```

본문·조각·설정을 고친 뒤 같은 파일:

```
$ uv run pytest tests/test_legal_checklist.py -q
4 failed, 113 passed in 126.72s (0:02:06)
```

남은 4개는 내가 쓴 **역방향** 테스트(`test_rendered_section_ids_are_all_in_the_checklist`)가 잡은
실제 누락이었다: ① 조각의 `<h2 id="business-info-heading">` 가 절 id(`business-info`)와 달라 절이
두 개로 세어졌다 → id 를 `<h2>` 에 직접 달았다 ② 약관의 `account`·`rules`·`service-changes`·
`liability`·`terms-changes` 절이 체크리스트에 근거 행이 없었다 → 약관규제법 §3·§7, 전상법 §13②4
행 5개를 추가했다. 테스트가 "표가 문서보다 늦게 늘는 것" 을 실제로 잡았다는 증거다.

### 3.2 법적 문서 3개 파일 (수정 후)

```
$ uv run pytest tests/test_legal_checklist.py tests/test_legal_pages.py tests/test_account_delete_page.py -q
........................................................................ [ 28%]
........................................................................ [ 57%]
............................................F........................... [ 86%]
..................................                                       [100%]
FAILED tests/test_legal_pages.py::test_transfer_section_en_states_real_opt_outs[even without a linked account]
1 failed, 249 passed in 273.76s (0:04:33)
```

실패 원인은 법 내용이 아니라 **줄바꿈**이었다 — en 본문의 `<strong>even without a linked\n  account</strong>`
가 문구를 두 줄로 쪼개서 기존 테스트의 부분 문자열 검사가 떨어졌다. 그 문장만 다시 감싸 고쳤다.

### 3.3 전체 스위트 (로컬 `main` = `4d83feb` 위로 rebase 한 뒤)

```
$ uv run pytest -q
........................................................................ [ 94%]
........................................................                 [100%]
992 passed in 829.01s (0:13:49)
(exit=0)
```

### 3.4 ruff

```
$ uv run ruff check .
All checks passed!
(exit=0)
```

`ruff format --check` 는 레포 전체가 포맷 대상이 아니어서(기존 227개 통과·39개 미포맷) 돌리지 않았다 —
CI(`.github/workflows/ci.yml`)가 쓰는 명령은 `uv run ruff check .` 하나다.

## 4. `impeccable detect` — 0건

Jinja 템플릿을 직접 스캔하면 `url_for` 를 못 풀어 CSS 를 못 읽으므로(티켓 01·09·14 메모) **개발 서버를
띄워 URL 로** 돌렸다. 세션이 필요한 삭제 확인 폼은 `review/detect-snapshot-16.py` 로 렌더해
`web/static/` 아래에 임시로 떠서 같은 서버의 URL 로 스캔했다(확인 후 삭제 — `git status` clean).

사용 바이너리: `/Users/saem/.impeccable/bin/0.1.14/impeccable`.

```
$ FLASK_ENV=testing uv run flask --app wsgi run --port 5116      # (백그라운드)

$ impeccable detect "http://127.0.0.1:5116/privacy?lang=ko"            → (출력 없음) exit=0
$ impeccable detect "http://127.0.0.1:5116/privacy?lang=en"            → (출력 없음) exit=0
$ impeccable detect "http://127.0.0.1:5116/terms?lang=ko"              → (출력 없음) exit=0
$ impeccable detect "http://127.0.0.1:5116/terms?lang=en"              → (출력 없음) exit=0
$ impeccable detect "http://127.0.0.1:5116/account/delete?lang=ko"     → (출력 없음) exit=0
$ impeccable detect "http://127.0.0.1:5116/account/delete?lang=en"     → (출력 없음) exit=0
$ impeccable detect "http://127.0.0.1:5116/static/_t16_form_ko.html"   → (출력 없음) exit=0
$ impeccable detect "http://127.0.0.1:5116/static/_t16_form_en.html"   → (출력 없음) exit=0
$ impeccable detect web/static/legal.css                               → (출력 없음) exit=0
$ impeccable detect web/static/account.css                             → (출력 없음) exit=0
```

**중간에 1건이 떴고 고쳤다**(숨기지 않고 적는다): `/privacy?lang=ko` 가 처음에
`[em-dash-overuse] 20 em-dashes in body text` advisory 를 냈다. 국외 이전 표의 "받는 자 — 공개 창구"
와 수탁자 제목의 줄표를 괄호·콜론으로 바꿔 ko 본문의 줄표를 20 → 6개로 줄이고(en 도 같은 부호로
맞춤), 다시 돌려 0건·출력 없음을 받았다. 처음 재실행 때 여전히 20개로 보인 건 `flask run` 이 Jinja
템플릿을 캐시하고 있었기 때문이라, 서버를 재시작해 `curl | grep -c "—"` = 6 을 확인한 뒤 스캔했다.

**"출력이 비었다" 가 "탐지기가 안 돌았다" 가 아님을 대조군으로 확인했다** — 폐기된 V2 목업
(`TOOLS.md` 에 7건으로 기록된 파일):

```
$ impeccable detect .scratch/store-launch/design/archive/v2_softdark_home.html
  [low-contrast] 2.8:1 (need 4.5:1) — text #f1f5f9 on #3fa66b
  … (생략)
  [overused-font] Primary font: inter
7 anti-patterns found.
```

디자인 쪽 판단: `design/SCREENS.md` "웹" 절이 `/privacy`·`/terms` 를 "같은 레이아웃의 문서 페이지"
로만 정하고 목업이 없어서, 09 가 만든 `legal.css`(OVERRIDES §10 의 480px 중앙 카드)를 그대로 썼고
**새 CSS·새 클래스를 만들지 않았다**. 국외 이전 5칸 고지는 480px 폭에서 5열 표가 깨지므로 표 대신
기존 `dl` + 중첩 `ul` 로 썼다 — 디자인 파일과 충돌하는 선택이 아니라 없는 패턴을 기존 패턴으로
대체한 것이고, 이유를 커밋 메시지에도 적었다.

## 5. 마이그레이션 heads

DB 변경이 없어 새 리비전을 만들지 않았다. 체인이 갈라지지 않았는지는 확인했다:

```
$ FLASK_ENV=testing uv run flask --app wsgi db heads
d7a1f0ca0a29 (head)
(1줄)
```

## 6. rebase·작업 트리

```
$ git rebase main
Successfully rebased and updated refs/heads/dosaem/t16-legal-compliance-checklist.

$ git log --oneline main..HEAD   # 이 문서 커밋 전
74dbcd4 fix(16): 구현하지 않은 보호조치 고지를 실제 처리에 맞게 고침 (green)
22ae240 test(16): 고지와 실제 처리 불일치 3건을 재현하는 테스트 (red)
1c0bda6 review(16): 법적 고지와 실제 처리 불일치 3건 보고
b195048 docs(16): 구현 증거 — 체크박스별 테스트 표, 992 passed, detect 0건
3ab9cf9 docs(16): 체크리스트 링크·사람 확인 항목·미정 9·21·22·23 결과 기록
a468eb1 feat(16): 방침·약관을 법 필수 기재사항으로 보완하고 사업자 정보를 조각으로 분리 (green)
e6218d6 test(16): 법 기준 체크리스트와 조문→절→테스트 묶음 (red)
(이 문서 커밋 전 기준 7개 — 라운드 1 의 5개 + test/fix 2개)

$ git status --short
(빈 출력 — clean)
```

`impeccable detect` 0건 재확인(문구를 바꾼 `/privacy` 두 언어 + 안 바꾼 `/terms` 두 언어).
`FLASK_ENV=testing uv run flask --app wsgi run --port 5116` 으로 띄우고 0.1.14 바이너리로 돌렸다:

```
$ impeccable detect "http://127.0.0.1:5116/privacy?lang=ko"   → (출력 없음) exit=0
$ impeccable detect "http://127.0.0.1:5116/privacy?lang=en"   → (출력 없음) exit=0
$ impeccable detect "http://127.0.0.1:5116/terms?lang=ko"     → (출력 없음) exit=0
$ impeccable detect "http://127.0.0.1:5116/terms?lang=en"     → (출력 없음) exit=0
$ impeccable detect --json "http://127.0.0.1:5116/privacy?lang=ko"   → []  exit=0
$ impeccable detect --json "http://127.0.0.1:5116/privacy?lang=en"   → []  exit=0
$ impeccable detect web/static/legal.css                       → (출력 없음) exit=0
```

문장을 늘리면서 ko 본문 줄표가 6 → 8개가 됐지만(라운드 1 에서 20개가 `em-dash-overuse` advisory 를
냈던 지점) 이번엔 0건이다. `LEGAL_EFFECTIVE_DATE` 는 그대로 **2026-10-14** 다 — 수정일이 같은 날이라
올릴 날짜가 없다(숨기지 않고 적는다).

### 하지 않은 것 (이 라운드)

- `scripts/backup.sh`·`Dockerfile`·`docker-compose.prod.yml`·앱 코드 변경 없음. 백업 덤프 암호화와
  접속기록 보관은 **출시 전 사람 결정 항목**으로만 남겼다
- `review/impl-review-16.md` 는 고치지 않았다. 프로덕션 접근·`git push`·실제 외부 서비스 호출·NAS
  접근 없음. 하위 워커·서브에이전트 띄우지 않았다

## 수정 라운드 2

- 대상: `review/impl-review-16.md` "## 라운드 2" 의 결함 **D-16-4 (MAJOR) 1건**. 같은 절의 이전 결함
  D-16-1·2·3 은 리뷰가 FIXED 로 판정했고 REPEAT 은 없다. BLOCKER 0 / MINOR 0.
- 커밋 2개: `test(16)` 재현 테스트(red) → `fix(16)` 고지 수정(green). `review/impl-review-16.md` 는
  고치지 않았다.
- 코디네이터 지시(`msg_71328848e48a`, "수정 원칙")를 그대로 따랐다: **D-16-4 하나만**, 실제 동작대로,
  국외 이전 Apple 행 + 보유 기간 절에 반영, 다른 문장은 건드리지 않음.

### D-16-4 — 애플 연결 철회를 "이전이 없는" 범위에 넣어 실제 철회·재시도 전송과 충돌 (MAJOR)

**원인.** 고지 범위를 코드 경로가 아니라 "연결이 있으면 전송, 없으면 미전송" 이라는 직관으로 묶었다.
실제 경로는 반대다 — 연결을 끝내는 행위가 전송을 **일으킨다**:

- `app/services/account_deletion_service.py:56`~`:69` — `schedule_revocation` 으로 철회 의무를 적고
  Account/Guest 를 **먼저 커밋해 지운 뒤** `complete_scheduled_revocation` 으로 애플을 호출한다.
  즉 계정 행이 사라진 상태에서 refresh token 이 애플로 나간다.
- 실패하면 그 행이 `AppleRevocationRetry` 에 남고
  `app/services/apple_revocation_service.py:64`~`:101` 의 Beat 태스크가 `RETRY_MAX_AGE = 7일`
  동안 날마다 다시 보낸다. 토큰은 연결 계정이 없어도 존재한다.

그래서 en 의 "the Apple refresh token exists only for a linked account" 는 사실과 어긋났고,
같은 방침의 보유 기간 절(ko `:57`, en `:59` — "철회 실패 시 재시도용으로 최대 7일 보관")과도
한 문서 안에서 모순이었다. 리뷰어의 지적은 맞다 — 반박하지 않는다.

**기존 테스트가 왜 놓쳤는가.** `test_store_rows_do_not_claim_unlinking_stops_every_transfer` 는
"로그인/Sign-in" 이 "이전이 없"보다 **앞에 오는지** 순서만 봤다. 그래서 그 범위에
"·연결 철회 / and revocation" 을 덧붙인 문장도 그대로 통과했다. 범위에 무엇이 **들어가서는 안 되는지**
를 보지 않은 것이 빈틈이었다.

**수정 내용.**

- `web/templates/legal/privacy.ko.html:171`, `web/templates/legal/privacy.en.html:185` — Apple 행의
  "거부 방법·효과" 를 세 경우로 갈랐다: ① **로그인** — 연결하지 않으면 이전 없음(철회를 이 범위에서
  뺐다) ② **연결 철회** — 이전을 멈추는 수단이 아니라 그 자체가 이전이며, 연결한 계정을 삭제하면
  보관한 refresh token 을 철회를 위해 애플로 보내고, 실패하면 계정 기록이 지워진 뒤에도 토큰만 남겨
  최대 7일 날마다 다시 보낸 뒤 폐기하고, 한 번 연결한 뒤에는 이 전송을 거부할 수 없다 ③ **구독 검증**
  — 종전과 같다(건드리지 않았다). ko/en 이 같은 내용이다.
- `docs/legal-checklist.md` 개보법 §28의8②5 행 — "애플 행은 연결 철회를 또 갈라 적는다" 요구와
  새 테스트 2개를 매핑에 넣었다(조문 → 요구 → 절 id → 확인 테스트 사슬 유지).
- **보유 기간 절은 바꾸지 않았다.** 코디네이터가 반영을 지시한 "철회 재시도 기록은 최대 7일 보관 후
  폐기" 는 이미 ko `:53`~`:57`("보유 기간: 계정 삭제 시 폐기하며, 철회 요청이 실패하면 재시도용으로
  최대 7일 보관한 뒤 폐기")·ko `:229`("철회가 끝나면 즉시, 철회가 실패하면 최대 7일 후 폐기")와
  en `:55`~`:59`·`:244` 에 같은 내용으로 적혀 있다. 코드(`RETRY_MAX_AGE`)와 대조해 일치를 확인했고,
  "다른 문장은 건드리지 마라" 에 따라 같은 말을 다시 쓰지 않았다.
- 앱·설정·DB·`scripts/` 변경 없음. 고친 것은 고지 문구와 체크리스트 매핑뿐이다.

**증명하는 테스트.** `tests/test_legal_pages.py` 에 애플 행만 보는 2개 × ko/en = 4 케이스를 추가했다
(기존 순서 테스트는 그대로 둔 채):

- `test_apple_row_discloses_revocation_as_a_transfer` — 거부 방법 칸에 "연결 철회",
  "연결한 계정을 삭제하면", "철회를 위해 Apple 로 전송", "7일"(en: `Revocation`,
  `delete an account you linked`, `send the Apple refresh token`, `7 days`)이 있어야 한다.
- `test_apple_row_does_not_fold_revocation_into_the_no_transfer_scope` — "이전이 없"/`there is no
  transfer` **앞** 구간에 "철회"/`revocation` 이 나오면 실패한다. 이번 결함의 문장 모양을 직접 막는다.

red (수정 전, `ae38d72`):

```
$ uv run pytest tests/test_legal_pages.py -q -k "apple_row or unlinking"
FAILED tests/test_legal_pages.py::test_apple_row_discloses_revocation_as_a_transfer[ko]
FAILED tests/test_legal_pages.py::test_apple_row_discloses_revocation_as_a_transfer[en]
FAILED tests/test_legal_pages.py::test_apple_row_does_not_fold_revocation_into_the_no_transfer_scope[ko]
FAILED tests/test_legal_pages.py::test_apple_row_does_not_fold_revocation_into_the_no_transfer_scope[en]
4 failed, 4 passed, 103 deselected in 4.77s
```

실패 메시지가 결함 문장을 그대로 집어낸다(en 사례):

```
E       AssertionError: 애플 en: 연결 철회를 '이전이 없다' 범위에 넣었다 — 철회는 토큰을 애플로 보낸다
E         'revocation' is contained here:
E           gn-in and revocation</strong> &mdash; if you never link an apple account, or unlink it,
```

green (수정 후):

```
$ uv run pytest tests/test_legal_pages.py -q -k "apple_row or unlinking or separate_sign_in"
12 passed, 99 deselected in 8.21s

$ uv run pytest tests/test_legal_checklist.py tests/test_legal_pages.py -q
244 passed in 232.06s (0:03:52)
(exit=0)
```

리뷰가 D-16-4 의 실제 경로 근거로 든 애플 철회 테스트도 회귀 없음을 함께 확인했다(§R2.2 전체 스위트).

### R2.1 틀렸다고 판단해 고치지 않은 지적

없다. 라운드 2 의 유일한 결함 D-16-4 는 코드 경로로 재현되는 실제 불일치였고 그대로 고쳤다.
리뷰의 "증거 부족"(impeccable URL 검사 미재실행)은 리뷰어 쪽 실행 범위의 한계를 적은 것이라
결함으로 받지 않았고, 아래 §R2.3 에서 URL 검사를 다시 돌려 0건을 붙인다.

### R2.2 전체 테스트 · ruff · heads · rebase

로컬 `main` = `24c584d` 위로 rebase 한 뒤 전용 자원(DB `chosung_daily_test_t16`, Redis DB 4,
마이그레이션 DB `chosung_daily_test_t16_migrations`)으로 실행했다. 공용 테스트 DB 는 건드리지 않았다.
접속 URL 의 자격증명 값은 이 문서에 적지 않는다.

```
$ uv run pytest -q
........................................................................ [ 97%]
.................................                                        [100%]
1257 passed in 783.15s (0:13:03)
(exit=0)
```

라운드 1 의 1253건 → 1257건. 늘어난 4건이 이번에 추가한 D-16-4 재현 케이스다(실패·에러·skip 0).

```
$ uv run ruff check .
All checks passed!
(exit=0)
```

```
$ FLASK_ENV=testing SENTRY_DSN='' uv run flask --app wsgi db heads
d7a1f0ca0a29 (head)
(1줄 — 이 티켓의 마이그레이션 변경 없음)
```

```
$ git rebase main                      # 로컬 main = 24c584d. origin/main 은 쓰지 않았다
Successfully rebased and updated refs/heads/dosaem/t16-legal-compliance-checklist.

$ git diff main...HEAD --check
(exit=0)

$ git status --short
(빈 출력 — clean)

$ git log --oneline main..HEAD         # 이 문서 커밋 전
e7a5d21 fix(16): 애플 연결 철회를 거부 수단이 아니라 이전으로 고쳐 고지 (green)
db47dc7 test(16): 애플 연결 철회 고지가 실제 전송과 어긋나는 것을 재현하는 테스트 (red)
66854fb review(16): 라운드 2 재검증 및 Apple 철회 고지 결함 보고
4936b36 docs(16): 수정 라운드 1 증거 — 결함별 원인·수정·증명, 1253 passed·ruff·detect 0건
88f60ce fix(16): 구현하지 않은 보호조치 고지를 실제 처리에 맞게 고침 (green)
76fe9b7 test(16): 고지와 실제 처리 불일치 3건을 재현하는 테스트 (red)
b18d423 review(16): 법적 고지와 실제 처리 불일치 3건 보고
ae84095 docs(16): 구현 증거 — 체크박스별 테스트 표, 992 passed, detect 0건
3da7d47 docs(16): 체크리스트 링크·사람 확인 항목·미정 9·21·22·23 결과 기록
0e2108c feat(16): 방침·약관을 법 필수 기재사항으로 보완하고 사업자 정보를 조각으로 분리 (green)
a9de1f7 test(16): 법 기준 체크리스트와 조문→절→테스트 묶음 (red)
```

### R2.3 `impeccable detect` — 0건 (URL 재검사 포함)

라운드 1 과 같은 방법(개발 서버 + URL, 세션 폼은 `review/detect-snapshot-16.py` 스냅샷)으로 돌렸다.
바이너리는 `~/.impeccable/bin/0.1.14/impeccable` — **엔진 버전은 `--version` = 4.0.0** 이다(디렉터리
이름이 플러그인 버전이라 라운드 1 의 "0.1.14" 와 같은 바이너리다. PATH 에 `impeccable` 은 없어서
절대 경로로 불렀다).

```
$ FLASK_ENV=testing SENTRY_DSN='' uv run flask --app wsgi run --port 5126   # (백그라운드)
$ uv run python review/detect-snapshot-16.py
wrote web/static/_t16_form_ko.html (2545 bytes)
wrote web/static/_t16_form_en.html (3330 bytes)

$ impeccable detect "http://127.0.0.1:5126/privacy?lang=ko"           → (출력 없음) exit=0
$ impeccable detect "http://127.0.0.1:5126/privacy?lang=en"           → (출력 없음) exit=0
$ impeccable detect "http://127.0.0.1:5126/terms?lang=ko"             → (출력 없음) exit=0
$ impeccable detect "http://127.0.0.1:5126/terms?lang=en"             → (출력 없음) exit=0
$ impeccable detect "http://127.0.0.1:5126/account/delete?lang=ko"    → (출력 없음) exit=0
$ impeccable detect "http://127.0.0.1:5126/account/delete?lang=en"    → (출력 없음) exit=0
$ impeccable detect "http://127.0.0.1:5126/static/_t16_form_ko.html"  → (출력 없음) exit=0
$ impeccable detect "http://127.0.0.1:5126/static/_t16_form_en.html"  → (출력 없음) exit=0
$ impeccable detect web/static/legal.css                              → (출력 없음) exit=0
$ impeccable detect web/static/account.css                            → (출력 없음) exit=0
$ impeccable detect --json ".../privacy?lang=ko" ".../privacy?lang=en"  → []
```

"출력이 비었다" 가 "탐지기가 안 돌았다" 가 아님을 라운드 1 과 같은 대조군으로 다시 확인했다:

```
$ impeccable detect .scratch/store-launch/design/archive/v2_softdark_home.html
  [overused-font] Primary font: inter
  … 7 anti-patterns found.
```

이번 수정이 ko 본문 줄표를 늘리지 않았는지도 확인했다(라운드 1 에서 `em-dash-overuse` advisory 를
냈던 지점): 문장을 콜론·세미콜론으로 이었고 `curl .../privacy?lang=ko | grep -c "—"` = **8** 로
라운드 1 과 같다. 스냅샷 HTML 2개는 확인 후 지웠다(`git status` clean).

`LEGAL_EFFECTIVE_DATE` 는 그대로 **2026-10-14** — 수정일이 같은 날이라 올릴 날짜가 없다.

### R2.4 미수정 MINOR (리뷰 결함 아님 — 관찰 기록)

리뷰 라운드 2 의 MINOR 는 0건이라 고칠 MINOR 는 없었다. 다만 D-16-4 를 조사하다 **고지 범위와
구현의 비슷한 틈 1건을 봤고, 고치지 않았다** — 숨기지 않고 적는다:

- `web/templates/legal/privacy.ko.html:50` "보유 기간: **연결 해제** 또는 계정 삭제 시까지",
  en `:52` "until you **unlink** or delete your account" 는 "연결 해제" 기능을 전제하지만,
  이 레포에 연결 해제 경로는 없다(`app/api/*` 에 unlink 라우트 없음, `app/web.py` 는 `/`,
  `/privacy`, `/terms`, `GET|POST /account/delete` 뿐). 연결을 끝내는 유일한 수단이 계정 삭제다.
- 왜 안 고쳤나: ① 이 문장은 티켓 16 이 만든 것이 아니다 — `git show main:web/templates/legal/privacy.ko.html`
  에 "연결 해제 또는 계정 삭제 시 삭제합니다" 로 이미 있었고 16 은 "보유 기간:" 꼴로 바꿔 적기만 했다
  ② 리뷰어가 결함으로 올리지 않았다 ③ 코디네이터 지시가 "D-16-4 하나만 고친다 / 다른 문장은 건드리지
  마라" 였다. 범위를 넘지 않으려 관찰로만 남긴다 — 고치려면 두 줄(ko·en)에서 "연결 해제 또는" 을
  빼면 된다.

### 하지 않은 것 (이 라운드)

- 앱·설정·DB·마이그레이션·`scripts/`·`docker-compose*`·`Dockerfile` 변경 없음. 바꾼 파일은
  `web/templates/legal/privacy.{ko,en}.html`, `docs/legal-checklist.md`, `tests/test_legal_pages.py`,
  이 문서뿐이다
- `review/impl-review-16.md` 는 고치지 않았다. 범위 밖 리팩토링·기능 추가 없음
- 프로덕션 접근·배포·`git push`·실제 외부 서비스 호출 없음(애플·스토어 경계는 전부 테스트 대역).
  계정·결제·인증 정보 입력 없음. 시크릿 값을 파일·로그·문서에 적지 않았다. NAS 접속 없음
- 하위 워커·Claude 서브에이전트·`claude --bg`·claude-handoff 쓰지 않았다
