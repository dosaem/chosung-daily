# 티켓 37 구현 증거 — 릴리스 문서 완성 · 실기기 체크리스트 · 설계 판단 항목 점검

작업: Phase3 Implementer (task_feb20b235733), 2026-10-15.
브랜치 `dosaem/t37-release-docs-device-checklists`, 로컬 `main`(3463865) 위로 rebase.

문서 티켓이라 "동작" 이 아니라 **문서와 코드·워크플로의 일치**가 검증 대상이다. 그래서
새 테스트 두 묶음(`tests/test_release_docs.py` 신규, `tests/test_domain_docs.py` 확장)이
그 일치를 묶는다 — 통합 목차를 사람이 손으로 옮겨 적게 두면 원본이 늘 때 조용히 거짓이
되기 때문이다.

## 1. TDD — red → green

| 단계 | 명령 | 결과 |
|---|---|---|
| red (문서 수정 전) | `uv run pytest tests/test_release_docs.py tests/test_domain_docs.py -q` | `39 failed, 4 passed, 53 errors` — 통합 목차·체크리스트·§C.32 점검표·KST 절·면접 범위 문장·스펙 상태 표가 전부 없어서 fixture 단계에서 깨졌다 |
| green (RELEASE·README·CONTEXT·ADR·spec 수정 후) | 같은 명령 | `101 passed`(release-docs) + `8 passed`(domain-docs) |
| red 재확인 (옛 번호) | `test_old_ticket_numbers_are_renumbered` 11 케이스 | 수정 전 전부 fail(구 번호 존재), 수정 후 전부 pass |

red 단계 출력(발췌):

```
ERROR tests/test_release_docs.py::test_device_checklist_covers_every_item_the_spec_asks_for[Sandbox]
ERROR tests/test_release_docs.py::test_c32_checklist_lists_every_design_decision_item[KST 고정]
FAILED tests/test_release_docs.py::test_readme_flutter_section_states_the_interview_scope
FAILED tests/test_release_docs.py::test_open_undecided_items_are_marked_for_operational_data[1]
39 failed, 4 passed, 53 errors in 0.49s
```

## 2. 실행한 검증 (전부 실제로 돌렸다)

전용 자원을 썼다 — `TEST_DATABASE_URL=…/chosung_daily_test_t37`,
`TEST_REDIS_URL=redis://localhost:6379/11`,
`TEST_MIGRATION_DATABASE_URL=…/chosung_daily_test_t37_migrations`.
공용 테스트 DB(`chosung_daily_test`)·Redis DB 1 은 건드리지 않았고, 이미 떠 있던
`chosung-daily-mysql-1`·`chosung-daily-redis-1` 컨테이너를 그대로 썼다(내리지 않았다).

| 명령 | 결과 |
|---|---|
| `uv run ruff check .` | `All checks passed!` |
| `uv run ruff format --check tests/test_release_docs.py tests/test_domain_docs.py` | `2 files already formatted` (레포 전체는 `ruff format` 를 쓰지 않는다 — CI 는 `ruff check` 만 돈다) |
| `uv run pytest tests/test_release_docs.py tests/test_domain_docs.py -q` | `101 passed` / `8 passed` |
| `uv run pytest tests/test_deploy_workflow.py -q` | `17 passed` — secrets 표를 통합 목차로 옮긴 뒤에도 기존 `test_deploy_secrets_are_documented` 가 통과한다(그 파서는 **첫** secrets 제목의 표를 읽으므로, 통합 목차가 모든 secret 을 담아야 깨지지 않는다) |
| `uv run pytest -q` (전체) | PYTEST_FULL |
| `cd mobile && flutter analyze` | `No issues found! (ran in 17.7s)` |
| `cd mobile && flutter test` | `All tests passed!` — 782 tests |
| `uv run flask db heads` | 마이그레이션을 만들지 않았다(아래 §7) |

Flutter 빌드 산출물은 만들지 않았다(`analyze`·`test` 만) — `mobile/build` 는 그대로다.

## 3. 티켓 체크박스별 근거

| 체크박스 | 무엇을 했나 | 무엇이 증명하나 |
|---|---|---|
| ① `docs/RELEASE.md` D0~D3 체크리스트 + NAS 첫 배포 + 복구 리허설 + GitHub secrets 표 통합 | 새 절 3개: `## 사람 작업 순서 (D0~D3)`, `## GitHub Actions secrets · variables 통합 목차`, `## 실기기 체크리스트 (통합)`. 티켓별 `### NN.` 절은 배경으로 남겼다 | `test_human_order_has_every_stage`(D0~D3 4개) · `test_human_order_names_both_operator_accounts`(운영자 계정 두 개) · `test_d2_names_the_grace_period_and_the_asc_name_clash`(Grace Period·16일·"Hidden Vowels: Daily Word") · `test_d3_rechecks_the_submission_day_requirements`(target SDK·Billing 8·Data safety·`/account/delete`) · `test_d3_includes_the_nas_first_deploy_and_the_restore_rehearsal`(`docker volume ls`·복구 리허설) · `test_secret_index_covers_every_secret_the_workflows_use`(워크플로의 `secrets.*` 21개 전부) · `test_variable_index_covers_every_variable_the_workflows_use`(`vars.*` 9개) · `test_secret_index_rows_point_at_a_detail_section` · `test_secret_index_does_not_carry_values` · `test_human_order_items_point_at_a_detail_section` |
| ② 실기기 체크리스트 통합 (각 항목 기대 결과) | 41개 항목을 알림·구독·광고·계정/삭제·태블릿 다섯 소절로. 모든 항목이 `조작 → 기대 결과` 꼴 | `test_device_checklist_has_a_subsection_per_area`(5개) · `test_every_device_checklist_item_states_an_expected_result`(41개 전부 `→` 포함, 하한 20) · `test_device_checklist_covers_every_item_the_spec_asks_for`(cold·warm·같은 날·다음 날·iOS·Android·Sandbox·복원·pending·4040010·유예·UMP·ATT·새 게스트·iPad·rail·배너·결과 시트·Split View·가로 20개 키워드) |
| ③ 티켓 16 의 법적 항목을 D1·D3 에 통합 | D1 = 통신판매업(면제 결정)·보호책임자·주소/전화·전문가 검토(안 받음), D3 = Data safety 일치 대조·스토어 구독 고지 일치·ASC EULA 비워 두기 확인 | `test_legal_items_from_ticket_16_are_in_the_d1_or_d3_stage`(통신판매업·보호책임자·주소·전문가·EULA·Data safety 6개) |
| ④ README "설계 판단" §C.32 열 항목 점검 | `### 37. 설계 판단 항목 점검 (§C.32)` 에 항목 → 절 목차 표. **빠진 것은 하나뿐이어서**(KST 고정) `### 37. KST 고정` 을 근거·대안 한 단락으로 새로 썼다 | `test_c32_checklist_lists_every_design_decision_item`(10개 항목 키워드) · `test_c32_checklist_points_at_sections_that_exist`(표가 가리킨 제목 전부가 실제 `### ` 절) · `test_readme_has_a_kst_design_decision` |
| ⑤ README Flutter 절 최종 + 면접 설명 범위 문장 | `### 22.` 끝에 "**면접 설명 범위.**" 문단 + 세 축(상태 흐름·SDK 선택·테스트 경계) → 뒷 티켓 절 색인 표 | `test_readme_flutter_section_states_the_interview_scope` · `test_readme_flutter_section_indexes_the_later_app_tickets`(권한 재확인 타이머·로컬 알림) |
| ⑥ 스펙 미정 항목 갱신 | `## 미정 항목` 끝에 `(티켓 37 반영)` 블록 — 번호 1~27 최종 상태 표 | `test_the_spec_records_a_final_status_for_every_undecided_item`(1~27 전부) · `test_settled_undecided_items_name_the_ticket_that_settled_them`(9·12·13·14·18·19·20·21·22·23·24) · `test_open_undecided_items_are_marked_for_operational_data`(1·6·10·11 = "운영 데이터 후") |
| ⑦ `docs/agents/`·`CONTEXT.md`·`docs/adr/` 대조 | 아래 §4 의 대조 결과. 용어 4개 추가, ADR 0003 한 문장 보강 | `test_glossary_covers_the_concepts_the_app_code_has`(4개 용어 ↔ 실제 소스 파일) · `test_adr_0003_matches_the_app_side_recheck_floor` · 기존 `test_context_md_is_at_repo_root`·`test_adrs_are_under_docs_adr`·`test_domain_doc_points_at_those_paths` |
| ⑧ 옛 티켓 번호 정리 | 11곳(아래 §5) | `test_old_ticket_numbers_are_renumbered` 11 케이스 — 구 번호 부재 + 신 번호 존재를 둘 다 본다 |

## 4. `docs/agents/` · `CONTEXT.md` · `docs/adr/` 대조 결과

| 문서 | 적힌 것 | 최종 코드 | 판정 |
|---|---|---|---|
| `docs/agents/domain.md` | 단일 컨텍스트: 루트 `CONTEXT.md` + `docs/adr/` | `CONTEXT.md` 1개, `docs/adr/` 3개, `CONTEXT-MAP.md` 없음 | 일치 |
| `docs/agents/issue-tracker.md` | `.scratch/<slug>/spec.md` + `issues/NN-slug.md`, `Status:` 줄, `Blocked by:` 줄 | 실제 그 구조. 38개 파일 모두 `**Status:** ready-for-agent` | 일치(실제 표기는 `**Status:**` 로 굵게 — 마크다운 장식 차이라 고치지 않았다) |
| `docs/agents/README.md` | "레포 루트에 `CLAUDE.md` 가 아직 없다" + 붙일 블록 초안 | `ls CLAUDE.md` → 없음 | 일치 |
| `docs/agents/triage-labels.md` | 기본 5개 라벨 | 티켓 파일은 `ready-for-agent` 만 쓴다(나머지는 미사용) | 일치(미사용 라벨은 모순이 아니다) |
| `docs/adr/0001` (KST) | KST 자정 고정 | `app/config.py` `KST = ZoneInfo("Asia/Seoul")`, 앱은 `NotificationPlan.kstOffset` 고정 +9 | 일치. README 절이 없었으므로 `### 37. KST 고정` 추가 |
| `docs/adr/0002` (id_token 교환) | aud 매트릭스, 애플 refresh token 보관, Android 애플 미지원 | README "10." 의 aud 표·`provider_refresh_token` Fernet 암호화와 일치 | 일치 |
| `docs/adr/0003` (구독 권한) | 1h TTL + 만료 ±24h 5분 상한(티켓 13 때 갱신) | **티켓 33 이 더한 앱 쪽 하한 5분과 관측 시각이 빠져 있었다** | **보강** — 재조회 문단에 한 문장 추가 |
| `CONTEXT.md` | 게스트·계정·퍼즐·수익화·채널·안전성 확보조치 용어 | 앱 코드에 있는 **구독 안내(Paywall)·광고 동의(UMP)·권한 재확인·온보딩**이 용어집에 없었다 | **보강** — 용어 4개 추가(각각 `paywall_sheet.dart`·`google_ad_service.dart`·`entitlement_schedule.dart`·`onboarding_screen.dart` 가 짝) |
| `CONTEXT.md` 리더보드 | "익명 태그(게스트 번호 기반 16진 4자리)" | `puzzle_metrics.py` `f"{guest_id % ANON_TAG_MODULUS:04x}"` | 일치(티켓 38 반영분) |

## 5. 옛 티켓 번호 정리 — 고친 11곳과 "왜 그 11곳만인가"

대응표는 `review/plan-add-r1-response.md` §2(구 16→23, 구 23~34→25~36).

**찾는 방법.** `티켓 \d+` 를 코드·문서 전체에서 뽑고(229곳), 각 줄을
`git blame` → `git log --no-merges -S"<문구>"` 로 **그 줄을 만든 커밋의 티켓**을 찾아,
"번호 재배정 **전에** 머지된 티켓(01~13·15·17·19~22)이 쓴 줄이면서 가리키는 번호가
재배정 대상(16, 23~34)" 인 것만 골랐다. 재배정 **후** 머지된 티켓(23 이후)이 쓴 줄은
이미 신 번호다 — 예를 들어 `app/services/app_config_service.py:12` 의 "(토글 UI 는 티켓
23)" 은 티켓 08 이 "16" 으로 썼던 것을 티켓 23 이 `f07c184` 에서 이미 고쳐 뒀다.

| 파일:줄 | 구 → 신 | 왜 |
|---|---|---|
| `README.md:19` | 티켓 22~31 → 22~33 | Flutter 코드 티켓 범위. 티켓 지시 그대로 |
| `README.md:1221` | 티켓 27 → 29 (계정 연결·전환) | `docs(22)` 커밋이 쓴 줄 |
| `README.md:1221` | 티켓 28 → 30 (로컬 알림) | 〃 |
| `docs/RELEASE.md` "### 22." | 티켓 32 → 34 (서명·워크플로) | 〃 |
| `docs/RELEASE.md` "### 22." | 티켓 33 → 35 (스토어 자산) | 〃 |
| `docs/RELEASE.md` "### 22." | 티켓 08·16 → 08·23 (점검 토글) | 〃 |
| `app/services/word_service.py:265` | 티켓 16 → 23 (배정표) | `수정 15:` 커밋이 쓴 줄 |
| `app/services/word_service.py:303` | 티켓 16 → 23 (배정표) | `티켓 15:` 커밋이 쓴 줄 |
| `mobile/test/guest/guest_token_provider_test.dart:29` | 티켓 27 → 29 | `feat(22)` 커밋 |
| `mobile/test/guest/guest_token_provider_test.dart:55` | 티켓 28 → 30 | 〃 |
| `mobile/lib/config/firebase_bootstrap.dart:11` | 티켓 24 → 26 (분석) | `feat(22)` 커밋. 같은 판단을 `mobile/lib/main.dart:32` 는 이미 "티켓 26" 으로 적고 있었다(티켓 26 이 쓴 줄) |
| `mobile/lib/startup/startup_controller.dart:69` | 티켓 23·25 → 25·27 | `feat(22)` 커밋 |

**티켓 본문이 예로 든 `mobile/lib/screens/home_shell.dart` "티켓 29·30" 은 이미 없다** —
현재 파일에 `티켓` 문자열이 0건이다(티켓 24 의 태블릿 뼈대가 그 셸을 `AdaptiveScaffold`
로 바꾸면서 주석이 사라졌다). 고칠 것이 없어 건드리지 않았다.

**`.scratch/store-launch/issues/*.md` 와 스펙 Further Notes 의 "구 NN" 표기는 그대로
뒀다** — 계획 리뷰 r3 가 "리뷰 노트의 번호는 당시 번호로 이력 보존" 을 요구했고, 각
티켓 파일이 "위 노트의 번호는 당시 번호" 라고 명시한다. 이력 기록을 지우면 왜 그 줄이
생겼는지를 추적할 수 없다.

## 6. 코디네이터 추가 메모(msg_f7ce7bc4d71b) 반영

| 요구 | 반영 |
|---|---|
| 1) 티켓 38·39·40 도 출시 문서·체크리스트에 포함 | **39** = D0 "단어 CSV 검수·업로드"(`#6`) + 기존 `### 39.`. **38** = 사람 할 일이 없어 절이 없다는 것을 `### 37.` 에 명시하고, 남은 한계(D-38-1·D-38-2)를 "알려진 한계" 에. **40** = D3 "최종 스크린샷 재촬영(진행 중)" 항목 + "알려진 한계" 의 Play 폰 스크린샷 줄에 "결과는 40 머지 후 반영" |
| 2) 스펙 `티켓 범위 01~38` → `01~40` (D-39-2) | `spec.md` Further Notes 의 `issues/01~38` → `issues/01~40` + 38·40 은 계획 뒤 추가라 `issues/` 파일이 없다는 한 줄. `test_the_spec_ticket_range_includes_the_tickets_added_after_planning` 이 지킨다 |
| 3) 코드·문서의 옛 번호 주석 정리 | 위 §5. "구 NN" 표기는 `.scratch/` 의 이력 기록과 `### 37.` 의 설명뿐이고, 코드·README·RELEASE 에는 재배정 전 번호가 남아 있지 않다(`grep -rn "구 [0-9][0-9]"` 결과를 §5 에 적었다) |
| 4) 티켓별 사람 확인 항목을 D0~D3 로 모으고 `user-todo.md` 1~18 과 어긋나지 않게 | D0~D3 항목에 **`#1`~`#18`** 번호를 달았다. **상태는 적지 않았다** — "상태는 그 파일이 정본" 이라고 본문에 쓰고, 번호만 가리킨다(두 곳에 상태를 적으면 갈라진다). `user-todo.md` 는 읽기만 했다. `test_the_human_order_references_every_user_todo_number` 가 1~18 전부 걸려 있는지, `test_the_human_order_does_not_duplicate_user_todo_state` 가 정본 문장이 있는지 본다 |
| 5) MINOR 로 머지한 것을 "알려진 한계" 절에 모으기 | 새 절 `## 알려진 한계 (출시 시점)` — D-31-8 · D-33-3 · D-39-1 · D-38-1 · D-38-2 · 구독·권한 실기기 미검증 · 배너 어댑티브 높이 미실측 · Play 폰 스크린샷(티켓 40) · D-17-6(웹) · 법적 해석 2건. 각 행에 "사용자가 보는 것" 과 근거 문서. `test_known_limitations_section_collects_the_merged_minors`·`test_known_limitations_rows_cite_where_the_judgement_is_written` |

리뷰에서 **FIXED 로 닫힌 MINOR 는 넣지 않았다**(예 D-35-9, D-33-1·2, D-32-6 — 각 리뷰
최종 라운드가 FIXED·MINOR 0 으로 닫았다). 그래서 이 절은 "지금 열려 있는 것" 만 담는다.

## 7. 코드·스키마 변경 없음

- 마이그레이션 0개 → `flask db heads` 를 돌릴 이유가 없다(`migrations/versions/` 무변경).
- 앱·서버 **동작 변경 0건**. `app/services/word_service.py`·`mobile/lib/config/firebase_bootstrap.dart`·
  `mobile/lib/startup/startup_controller.dart`·`mobile/test/guest/guest_token_provider_test.dart`
  은 **주석 한 줄씩**만 바뀌었다(`git diff` 각 4·2·2·4줄). 그래서 `flutter analyze` 0 ·
  `flutter test` 782 통과가 회귀 없음의 근거다.
- 외부 서비스 호출·NAS 접속·`git push` 없음. 시크릿 값은 어디에도 적지 않았다
  (`test_secret_index_does_not_carry_values` 가 통합 목차에 키 전문·광고 앱 ID 가 들어오는
  것을 막는다).

## 8. 하지 않은 것 · 다음 사람이 알아야 할 것

- **`user-todo.md` #17 의 "백업 `age` 개인키" 표기가 구현과 다르다.** 실제 구현은
  `openssl cms -encrypt`(공개키 CMS 봉투)이고 `age` 는 backup 컨테이너의 `mysql:8`
  이미지에 없어서 쓰지 않았다(미정 27, README "36."). 그 파일은 다른 세션이 갱신 중이라
  **읽기만 했고 고치지 않았다** — 코디네이터가 그 세션에 전달해야 한다.
- **티켓 40 결과 미반영.** Play 폰 스크린샷을 AVD 로 찍는지 iPhone 시뮬레이터의 Android
  구성으로 찍는지는 40 이 머지된 뒤 `docs/RELEASE.md` "알려진 한계" 의 해당 줄과
  `### 35.` 에 적어야 한다. 자리는 만들어 뒀다.
- **실기기 체크리스트는 아무도 실행하지 않았다.** 이 티켓은 목록을 만들었을 뿐이고,
  41개 항목 전부가 사람 차례(D3)다. 실기기가 없으면 출시 전에 확인할 방법이 없다 —
  구독·광고 쪽은 특히 테스트로 대체 불가다(§6 의 "구독·권한 실기기 미검증").
- **스펙 미정 항목 표의 상태 어휘를 티켓 문구보다 넓혔다.** 티켓은 "남은 것은 '운영 데이터
  후' 로 표시" 라고 했지만, 실제로 열려 있는 넷(1·6·10·11)만 그 문구를 쓰고 나머지는
  사실대로 `범위 밖(다음 Phase / 보류)` · `사람 D2/D3` 로 적었다. 전부 "운영 데이터 후" 로
  적으면 Playwright E2E(5)나 UMP 문구(7)처럼 운영 데이터와 무관한 것이 거짓이 된다.
- **중복을 남겼다.** 실기기 항목은 티켓 30·31·32·29·14 절에도 그대로 있다. 통합 절을
  정본으로 선언하고 각 절은 배경으로 뒀다 — 티켓별 절의 줄이 그 티켓의 리뷰 결함 번호
  (D-32-1·D-32-4·D-32-5 등)와 묶여 있어서, 지우면 그 줄이 왜 생겼는지가 사라진다.
