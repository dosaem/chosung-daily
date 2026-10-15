# 티켓 46 최종 리뷰 — 라운드 1

- 대상: `dosaem/t46-e2e-fixes-1` = 로컬 `main`(`ee960dd`) + 커밋 1개(`70650ca`). 머지 베이스가
  로컬 main 과 같고 트리는 clean(`git status` 0줄).
- 읽은 것: 티켓 원문(6개 항목), `.scratch/store-launch/spec.md`, `git diff main...HEAD`
  (29 파일), `review/impl-evidence-46.md`, 디자인 시스템 OVERRIDES(토큰 변경 때문에).
- 증거를 믿지 않고 전부 다시 돌렸다(§1). 코드는 고치지 않았다.

## 1. 내가 다시 돌린 검증

| 검증 | 결과 |
|---|---|
| `uv run ruff check .` | All checks passed (exit 0) |
| `uv run pytest -q -p no:cacheprovider` (TEST_DATABASE_URL=…/chosung_daily_test_t46, TEST_MIGRATION_DATABASE_URL=…/chosung_daily_test_t46_migrations, TEST_REDIS_URL=…/6) | **1756 passed in 1064.15s (0:17:44)**, exit 0, FAILED/ERROR 0 |
| `flutter analyze --no-pub` | No issues found (exit 0, info 0) |
| `flutter test --no-pub` | +796 All tests passed (exit 0) |
| `E2E_TICKET=46 scripts/e2e_web.sh --reporter=line` | **48 passed (1.9m)**, exit 0. 스택: 5046/5146, `chosung_daily_e2e_t46`, Redis **14**(시작 전 dbsize 0). `down` 뒤 DB drop · Redis 14 flush, 내 스택 프로세스 0개 |
| E2E axe | 산출물 `axe-*.json` 50개, 위반 **0건** — `expectAxeClean` 의 known 목록이 비어 있어도 통과 |
| E2E 09-admin 폭 실측(`steps.log`) | mobile-390: `문서 390px · 표 487px · 상자 358px · 뷰포트 390px` / desktop-1280: `문서 1280px · 표 992px · 상자 992px`. 링크는 `page.goto` 우회 없이 실제 클릭(spec 확인) |
| `impeccable detect --json` | 스냅샷 **20장 × 기본 뷰포트 + 390×844 7장 + 320×844 2장 + 1280×900 1장 = 30회, 전부 0건**(exit 0). 생성: `review/detect-snapshots-46.py`(6장) · 티켓 23 `admin-detect-snapshot-23.py`(10장, 회귀) · 티켓 38 `web-detect-snapshots-38.py`(4장, `.message` 색이 바뀌어 회귀) |

네이티브 변경 없음(`mobile/` diff 0) → `flutter build apk` 는 대상 아님. 티켓 43 iOS 스택
(gunicorn 8043, celery `e2e-t43`)이 다른 worktree 에서 돌고 있었는데 포트·DB·Redis 가 다
달라 건드리지 않았다.

## 2. 체크박스별 충족 여부

| # | 티켓 항목 | 판정 | 근거(직접 확인) |
|---|---|---|---|
| 1 | D-42-1 `{{ t.copy }}` → dict.copy 메서드 렌더 | **충족** | `index.html:182` 가 `t["copy"]`. 템플릿 18개의 모든 `a.b` 를 `dir(dict)` 와 대조한 내 전수 검색도 `pagination.items`(SQLAlchemy 속성)·`stock.items()`(의도된 호출)만 남고 `t.copy` 는 사라졌다. 재발 방지 테스트 둘 — `test_template_never_reaches_a_dict_method_by_attribute`(템플릿 전체 `t.<dict메서드>` 금지)·`test_no_page_renders_a_python_object_repr`(8장 렌더에 `<built-in method` 등 4종 없음) — 모두 실제 렌더/파일을 본다. `test_template_only_uses_keys_that_exist` 는 첨자 모양도 세도록 넓혀 `copy` 키를 놓치지 않는다 |
| 2 | D-42-2 백업 코드 칸 라벨 | **충족** | `aria-label="{{ t['backup_code_label'] }}"`, 사전 ko/en 둘 다 추가. pytest `test_the_backup_code_box_has_an_accessible_name` + E2E `toHaveAttribute` + axe 50회 0건 |
| 3 | D-42-3 삭제 안내가 `restart()` 에 지워짐 | **충족** | `discardDeletedAccountState()` 는 `true/false` 만 돌려주고 `init()` 이 `await restart()` **뒤**에 띄운다. `restart()` 안에서 await 없이 떠 있는 `loadStats/loadLeaderboard/loadTodayStats/applyPuzzle` 이 `#message` 를 건드리지 않는 것을 app.js 에서 확인했다(실패는 전부 `showPuzzleState` 인라인 카드). 하네스 `init` 모드가 `init()` 을 통째로 돌려 `finalMessage` 를 보므로 순서 결함을 실제로 잡는다. E2E 06 은 `toHaveText(t.account_deleted)` 보통 단정 |
| 4 | D-42-4 390px 배정표 링크 | **충족** | 운영자 표 5개 전부 `.admin-table-scroll`(`overflow-x:auto`, `tabindex="0"`, focus-visible 외곽선). 실측 문서 390 = 뷰포트, E2E 가 실제 탭 |
| 5 | D-41-1 P8 임시 파일 try/finally | **충족** | 워크플로 5개의 `token()` 본문이 **동일**(공백 제거 md5 일치), `os.unlink` 가 `finally` 에. AST 테스트 5개 + 실행 테스트 2개(`openssl dgst` 만 `FileNotFoundError`, `tempfile.tempdir` 을 `tmp_path` 로 돌려 `*.p8` 0개 확인). 머리말 5개·RELEASE §41 서술이 "api_key.json 은 안 만들고 P8 는 try/finally 로 지운다" 로 사실과 일치 |
| 6 | iOS 키체인 확인 → 방침 누락은 RELEASE 사람 확인 항목 | **충족** | `privacy.ko.html:289`·`privacy.en.html:310` 이 localStorage 만 적고 앱 저장소·앱 삭제 후 잔존은 없음을 내가 확인. `mobile/assets/translations/{ko,en}.json` 에 keychain/보안 저장/재설치 문구 없음. 법적 문서는 안 고쳤고 `docs/RELEASE.md` "### 16." 체크박스 + "### 46." 상세 |
| 검증 | E2E 48/48, pytest·ruff·flutter, detect 0건, 46 배정표 추가 | **충족** | §1. `env.sh` 에 46→14 추가, `test_e2e_scripts.py` 의 `E2E_TICKETS`·`RESERVED_REDIS_DBS`(6 추가) 동기화, README 배정표 갱신 |
| 제약 | 범위 6개, push·NAS·배포·외부 호출·시크릿 금지 | **충족(1건 확인 요)** | diff 에 키·비밀번호 패턴 없음. 범위 밖 변경 1건 — `--color-destructive-text` 토큰(§3 참고 ③). `.scratch/` 미수정, `mobile/` 미수정 |

## 3. 결함

### D-46-1 (MINOR) — `test_no_helper_writes_the_api_key_to_disk` 가 쉘 스텝을 더 이상 보지 않는다

- 파일: `tests/test_asc_helper_workflows.py:99-114`
- 전: 워크플로 **파일 전체**에 `api_key.json` 이 없음을 단정. 후: `_step_source()`(heredoc 안
  Python 만)에서 없음을 단정. 머리말 주석이 그 이름을 말하게 되어 좁힌 것인데, 필요한 것보다
  많이 좁혔다.
- 재현: `asc-status.yml` 의 쉘 `run:` 스텝에
  `echo "$API_KEY_JSON" > fastlane/api_key.json` 한 줄을 넣는다 → 기대: 테스트 실패 /
  실제: **통과**(Python heredoc 밖이라 안 본다). 이전 판은 잡았다.
- 제안: 파일 전체를 보되 주석 줄(`^\s*#`)만 걷어내고 단정하거나, 쉘 `run:` 블록도 함께 본다.
- 심각도 MINOR: 지금 워크플로에는 그런 스텝이 없고, 앱 동작과 무관한 테스트 범위 축소.

## 4. 참고(취향·후속, 판정에 영향 없음)

- ① `.admin-table-scroll` 은 `tabindex="0"` 인데 `role`·접근 가능한 이름이 없다. 1040px 처럼
  스크롤이 생기지 않는 폭에서도 탭 정지점이 되고 스크린리더가 이름 없는 요소에 멈춘다. axe 는
  안 잡지만 `role="region" aria-label="<표 이름>"`(또는 `aria-labelledby` 로 caption)을
  붙이면 깔끔하다.
- ② `test_template_never_reaches_a_dict_method_by_attribute` 는 변수 `t` 만 본다. 다른 dict
  컨텍스트 변수가 생기면 같은 함정을 못 잡는다. 내 전수 검색으론 지금은 없다. Jinja 의
  `env.parse()` 로 `Getattr` 노드를 걷으면 변수명에 의존하지 않는다.
- ③ `--color-destructive-text` 토큰(§7)은 티켓 6개 밖이다. 증거는 코디네이터가 `ask` 로
  승인했다고 적었고(2026-10-16) 변경 자체는 좁고 옳다(글자 쓰임 4곳만, 면·테두리 유지, 다크
  5.63:1). 디자인 시스템 OVERRIDES 표에는 아직 없으니 코디네이터가 갱신 여부를 정한다.
- ④ D-42-8(E2E 43 ↔ pytest 43 의 Redis 13 겹침)은 이 티켓 범위 밖으로 남아 있다 — `env.sh`
  주석에 적혀 있다.
- ⑤ 리뷰 중 생성한 detect 스냅샷·E2E 산출물(`e2e-artifacts/`)은 gitignore 이고 레포에 남는
  변경은 이 파일뿐이다. 전용 DB `chosung_daily_test_t46`(+`_migrations`)은 관례대로 남겼다.

판정: PASS
