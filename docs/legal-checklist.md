# 법적 문서 체크리스트 (`/privacy`, `/terms`)

이 문서는 **어느 조문이 무엇을 요구하고, 그 요구가 문서의 어느 절에 있고, 어느 테스트가
그걸 지키는지** 를 한 표로 묶는다. 법적 문서는 내용이 길어서 "빠진 항목" 이 눈으로는 안
보인다 — 조문 → 절 id → 테스트의 세 칸을 묶어 두면, 절을 지우거나 id 를 바꾸면
`tests/test_legal_checklist.py` 가 먼저 깨진다.

- 대상 문서: `web/templates/legal/{privacy,terms}.{ko,en}.html` + 조각
  `web/templates/legal/_business_info.html`
- 절 id 는 **ko·en 이 같다**. 절 구조·순서도 같다(한 언어에만 있는 절 금지) —
  `tests/test_legal_checklist.py::test_section_ids_match_in_order_across_languages`
- 표 읽는 법: `문서·절 id` 칸의 `` `privacy#collection` `` 은
  "개인정보처리방침의 `id="collection"` 절" 이다. 테스트가 이 칸을 파싱해서
  두 언어 템플릿에 그 id 가 있는지 본다.

> **이 문서는 법률 자문이 아니다.** 워커(에이전트)가 조문 텍스트를 읽고 매핑한 결과이고,
> 출시 전에 사람이 확인할 항목 — 통신판매업 신고 대상 여부, 주소·전화 공개 범위,
> 보호책임자 지정, 필요 시 전문가 검토 — 은 `docs/RELEASE.md` "### 16." 에 체크박스로
> 있다. 조문 해석이 갈리는 지점은 그 절에 그대로 적어 두었다.

## 1. 개인정보 보호법 제30조 제1항 · 시행령 제31조 (처리방침 필수 기재사항)

| 근거(조문·정책) | 요구 내용 | 문서·절 id | 확인 테스트 |
|---|---|---|---|
| 개보법 §30①1 | 개인정보의 처리 목적 | `privacy#purposes` | `test_every_checklist_section_id_exists_in_both_languages` |
| 개보법 §30①3 / 시행령 §31①1 | 처리하는 개인정보의 항목 | `privacy#collection` | `test_deleted_data_names_are_a_subset_of_the_policy_items` |
| 개보법 §30①2 | 개인정보의 처리 및 보유 기간 | `privacy#collection` | `test_privacy_ko_has_the_required_phrases[14일]`, `[7일]` |
| 개보법 §30①2 (백업 보존) | 삭제 후에도 백업본에 남는 기간(14일) 고지 | `privacy#collection` | `test_privacy_ko_has_the_required_phrases[14일]`, `tests/test_legal_pages.py::test_privacy_states_backup_retention` |
| 개보법 §30①3 / §17 | 제3자 제공: 받는 자·목적·항목·보유 기간 | `privacy#third-parties` | `test_every_checklist_section_id_exists_in_both_languages` |
| 개보법 §30①3 / §26 | 처리 위탁: 수탁자·위탁 업무 | `privacy#processors` | `test_every_checklist_section_id_exists_in_both_languages` |
| 개보법 §30①4 / 시행령 §31①2 | 개인정보의 파기 절차·방법 (백업 덤프는 **공개키 암호화 — 구현됨**, 티켓 36) | `privacy#destruction` | `test_privacy_ko_has_the_required_phrases[파기]`, `test_destruction_section_describes_the_real_backup_protection`, `test_the_backup_script_encrypts_the_dump_with_a_public_key` |
| 개보법 §30①5 / §35~§37 | 정보주체와 법정대리인의 권리·의무와 행사 방법 | `privacy#rights` | `test_delete_page_is_linked_from_the_rights_section` |
| 개보법 §29 / 시행령 §30 | 안전성 확보 조치(암호화·접근 통제·접속기록) | `privacy#security` | `test_every_checklist_section_id_exists_in_both_languages`, `test_privacy_states_the_implemented_log_retention` (접속기록 **1년 보관·월 1회 점검 — 구현됨**, 티켓 36) |
| 개보법 §30①6 / §31 / 시행령 §32 | 개인정보 보호책임자의 **성명 또는 직책**·연락처 — **사용자 결정(2026-10-14): 직책 "운영자" + 이메일**(성명은 `LEGAL_PRIVACY_OFFICER` 를 채우면 표시) | `privacy#officer` | `test_privacy_ko_has_the_required_phrases[개인정보 보호책임자]` |
| 시행령 §31①3 | 열람 청구를 접수·처리하는 부서(창구) | `privacy#officer` | `test_privacy_ko_has_the_required_phrases[열람]` |
| 시행령 §31①4 / §63 | 권익 침해 구제 방법 — 개인정보침해신고센터(118), 개인정보 분쟁조정위원회(1833-6972) | `privacy#remedies` | `test_privacy_ko_has_the_required_phrases[118]`, `[1833-6972]` |
| 개보법 §30①7 / 시행령 §31①6 | 자동 수집 장치의 설치·운영과 거부 방법 — 쿠키(세션), 광고 식별자(IDFA/ADID), 분석 SDK | `privacy#automatic-collection` | `test_privacy_ko_has_the_required_phrases[광고 ID 초기화]`, `[쿠키]` |
| 개보법 §22의2 | 만 14세 미만 아동의 개인정보 처리(동의·미수집) | `privacy#children` | `test_privacy_ko_has_the_required_phrases[만 14세]` |
| 시행령 §31①5 / §31② | 처리방침 변경 시 시행일·변경 내용·고지 방법, 이전 버전 확인 방법 | `privacy#changes` | `test_privacy_ko_has_the_required_phrases[시행일]` |
| 개보법 §30①7의2 / §37의2 | 가명정보 처리·자동화된 결정 — **해당 없음** 을 명시 | `privacy#general` | `test_every_checklist_section_id_exists_in_both_languages` |

### 1-1. 개인정보의 안전성 확보조치 기준 (개인정보보호위원회 고시 제2023-6호)

개보법 §29 의 구체적 조치를 정한 고시다. 이 서비스에 걸리는 조문만 적는다 —
보관 기간을 **1년**으로 정한 근거가 여기 있다(티켓 36).

| 근거(조문·정책) | 요구 내용 | 문서·절 id | 확인 테스트 |
|---|---|---|---|
| 고시 §8① (접속기록의 보관) | 개인정보처리시스템 접속기록을 **1년 이상** 보관. 2년 이상은 ① 5만명 이상 정보주체 ② **고유식별정보·민감정보** 처리 ③ 기간통신사업자인 경우 — 이 서비스는 셋 다 아니므로(수집 항목에 주민등록번호·여권번호·생체정보·사상·건강 등이 없다) **법정 최소 1년 = `ACCESS_LOG_RETENTION_DAYS` 기본값 365** | `privacy#collection` · `privacy#security` | `test_privacy_states_the_implemented_log_retention`, `test_the_retention_period_in_the_notice_matches_the_setting`, `tests/test_access_log.py::test_the_default_retention_is_the_legal_minimum_of_one_year`, `tests/test_access_log.py::test_rows_past_the_retention_period_are_deleted`, `tests/test_access_log_file.py::test_rotated_files_past_the_retention_period_are_deleted` |
| 고시 §8② (점검) | 접속기록을 **월 1회 이상** 점검 | `privacy#security` | `tests/test_access_log.py::test_the_monthly_report_counts_actions_denials_and_verifies_the_chain`, `tests/test_cli.py::test_access_log_report_prints_counts_denials_and_the_chain_result` (실행은 사람 — `docs/RELEASE.md` "### 36.") |
| 고시 §8③ (위·변조 방지) | 접속기록이 위·변조·도난·분실되지 않도록 안전하게 보관 | `privacy#security` | `tests/test_access_log.py::test_verify_reports_the_row_where_the_chain_breaks`, `test_verify_detects_a_deleted_row_in_the_middle`, `test_the_repository_exposes_no_update_or_delete_path` |
| 고시 §7 (개인정보의 암호화) | 인증정보·고유식별정보의 저장·전송 암호화 — 이 서비스는 **고유식별정보를 처리하지 않고** 비밀번호도 없다(로그인은 구글·애플 OAuth). 암호화 대상은 애플 refresh token 과 백업 덤프다 | `privacy#security` · `privacy#destruction` | `tests/test_secret_crypto.py`, `test_the_backup_script_encrypts_the_dump_with_a_public_key` |
| 고시 §11 (재해·재난 대비) | 백업·복구 계획 — **적용 대상 아님**(10만명 이상 처리하는 대기업·중견기업·공공기관 또는 100만명 이상 중소기업). 그래도 매일 백업과 복구 리허설을 둔다(티켓 21·36) | `privacy#security` | `tests/test_backup_restore.py` |

> **조문 번호 주의.** 위 번호는 **고시 제2023-6호(시행 2023. 9. 22.)** 기준이다. 2025-10
> 개정(보유 규모별 차등화)에서 접속기록 조항은 1년 유예로 들어갔다고 보도돼 있어 조 번호가
> 바뀔 수 있다 — 보관 기간 자체(1년, 상향 요건 2년)는 같다. 출시 전에 국가법령정보센터의
> 현행 고시로 조 번호를 확인하는 체크박스는 `docs/RELEASE.md` "### 36." 에 있다.

## 2. 개인정보 보호법 제28조의8 (국외 이전 고지)

§28의8①3 경로를 쓴다: **계약의 체결·이행에 필요한 국외 이전이고, §28의8② 의 고지사항을
처리방침에 공개** 한다(별도 동의를 받지 않는다). 그래서 아래 다섯 행이 모두 처리방침
`privacy#overseas` 절의 표에 있어야 한다.

받는 자 연락처는 **각사가 공개한 개인정보 문서 URL·공개 창구만** 쓴다. 공개된 담당자
연락처를 찾지 못한 경우 "해당사 개인정보처리방침 참조" 로 적는다(연락처를 추정해 적지
않는다).

| 근거(조문·정책) | 요구 내용 | 문서·절 id | 확인 테스트 |
|---|---|---|---|
| 개보법 §28의8②1~5 | 이전 항목 / 국가·시기·방법 / 받는 자 이름·연락처 / 목적·보유 기간 / 거부 방법·절차·효과 — 표의 다섯 칸 | `privacy#overseas` | `test_privacy_ko_has_the_required_phrases[국외 이전]`, `test_overseas_section_lists_every_recipient` |
| 개보법 §28의8②(Google) | Google — 로그인 식별자·이메일, Play 구독 검증. 창구: `policies.google.com/privacy` | `privacy#overseas` | `test_overseas_section_lists_every_recipient[Google]` |
| 개보법 §28의8②(Apple) | Apple — 로그인 식별자·이메일, App Store 구독 검증. 창구: `www.apple.com/legal/privacy/` | `privacy#overseas` | `test_overseas_section_lists_every_recipient[Apple]` |
| 개보법 §28의8②(AdMob) | Google AdMob — 광고 식별자·광고 요청 정보. 창구: `policies.google.com/technologies/ads` | `privacy#overseas` | `test_overseas_section_lists_every_recipient[AdMob]` |
| 개보법 §28의8②(Firebase) | Firebase Analytics — 앱 사용 이벤트·앱 인스턴스 ID. 창구: `firebase.google.com/support/privacy` | `privacy#overseas` | `test_overseas_section_lists_every_recipient[Firebase]` |
| 개보법 §28의8②(Sentry) | Sentry — 오류 발생 시 요청 정보·스택. 창구: `sentry.io/privacy/` | `privacy#overseas` | `test_overseas_section_lists_every_recipient[Sentry]` |
| 개보법 §28의8②5 | 이전 거부 방법·절차와 **거부의 효과**(거부 수단이 없는 기능은 "서비스를 쓰지 않는 것" 뿐임을 명시). 스토어 행은 **로그인과 구독 검증을 갈라** 적는다 — 구독 검증은 계정 연결과 무관하게 전송된다. 애플 행은 **연결 철회를 또 갈라** 적는다 — 철회는 이전을 멈추는 수단이 아니라 refresh token 을 애플로 보내는 이전이고, 실패하면 계정이 지워진 뒤에도 최대 7일 다시 보낸다 | `privacy#overseas` | `test_privacy_ko_has_the_required_phrases[이전을 거부]`, `tests/test_legal_pages.py::test_transfer_section_ko_states_real_opt_outs`, `tests/test_legal_pages.py::test_store_rows_separate_sign_in_from_subscription_verification`, `tests/test_subscription_verify.py::test_verify_reaches_the_store_without_a_linked_account`, `tests/test_legal_pages.py::test_apple_row_discloses_revocation_as_a_transfer`, `tests/test_legal_pages.py::test_apple_row_does_not_fold_revocation_into_the_no_transfer_scope` |

## 3. 전자상거래법 (사업자 신원·거래조건·청약철회)

| 근거(조문·정책) | 요구 내용 | 문서·절 id | 확인 테스트 |
|---|---|---|---|
| 전상법 §10①1~5 | 사이버몰 운영자 신원: 상호·대표자·주소·전화번호·전자우편주소·사업자등록번호 — **사용자 결정(2026-10-14): 주소는 시·구까지만 + "상세 주소는 요청 시 이메일로 제공", 전화번호는 `LEGAL_BUSINESS_PHONE` 자리만 두고 비면 미표시** | `terms#business-info` · `privacy#business-info` | `test_every_checklist_section_id_exists_in_both_languages`, `tests/test_legal_pages.py::test_set_business_info_is_rendered` |
| 전상법 §10①(이용약관) | 이용약관을 사이버몰에 표시 | `terms#service` | `tests/test_legal_pages.py::test_cross_links_the_other_document` |
| 전상법 §10①(호스팅) | 호스팅서비스 제공자 — **자체 호스팅(운영자 소유 서버)** 이면 그렇게 적는다 | `terms#business-info` | `test_terms_ko_has_the_required_phrases[호스팅]` |
| 전상법 §13①1 | 통신판매업 신고번호(신고한 경우) — 비면 그 행을 렌더하지 않는다 | `terms#business-info` | `tests/test_legal_pages.py::test_partially_set_business_info_renders_only_filled_rows` |
| 전상법 §13②2~4 | 재화의 내용·가격·결제 주기·공급 시기 등 거래조건 | `terms#subscription` | `test_terms_ko_has_the_required_phrases[자동 갱신]` |
| 전상법 §13②5 / §17 | 청약철회의 기한·행사 방법·효과 — **스토어 결제의 환불 주체가 Apple/Google** 임을 명시 | `terms#withdrawal` | `test_terms_ko_has_the_required_phrases[청약철회]`, `[환불]` |
| 전상법 §17②5 / 시행령 §21의2 | 디지털콘텐츠: 제공이 개시된 부분은 철회가 제한될 수 있음을 고지 | `terms#withdrawal` | `test_terms_ko_has_the_required_phrases[디지털 콘텐츠]` |
| 전상법 §13②10 | 소비자 불만·분쟁 처리 창구(연락처) | `terms#governing-law` · `terms#business-info` | `test_every_checklist_section_id_exists_in_both_languages` |
| 약관규제법 §3 | 계약 조건을 약관으로 명시 — 계정 연결·백업 코드의 효과와 분실 시 복구 불가 | `terms#account` | `test_every_checklist_section_id_exists_in_both_languages` |
| 약관규제법 §3 | 이용자의 금지 행위와 위반 시 조치를 명시 | `terms#rules` | `test_every_checklist_section_id_exists_in_both_languages` |
| 약관규제법 §3 / 전상법 §13②4 | 서비스 변경·중단·종료의 고지와 남은 구독 기간 처리 | `terms#service-changes` | `test_every_checklist_section_id_exists_in_both_languages` |
| 약관규제법 §7 | 면책 범위 제한 — 법이 보장하는 소비자 권리를 약관으로 줄이지 않음을 명시 | `terms#liability` | `test_every_checklist_section_id_exists_in_both_languages` |
| 약관규제법 §3 | 약관 변경의 고지 방법과 동의 간주 | `terms#terms-changes` | `test_every_checklist_section_id_exists_in_both_languages` |

## 4. 스토어 정책 (구독 고지)

| 근거(조문·정책) | 요구 내용 | 문서·절 id | 확인 테스트 |
|---|---|---|---|
| Apple App Review 3.1.2(a) | 구독 제목·기간(결제 주기)·가격·자동 갱신 조건 | `terms#subscription` | `test_terms_ko_has_the_required_phrases[자동 갱신]`, `test_terms_en_has_the_required_phrases[auto-renew]` |
| Apple App Review 3.1.2(a) | 해지 방법(설정 > Apple 계정 > 구독) | `terms#subscription` | `test_terms_ko_has_the_required_phrases[App Store]` |
| Apple App Review 3.1.2(a) | 약관·개인정보처리방침 링크를 앱·스토어에서 접근 가능하게 | `terms#privacy` | `tests/test_legal_pages.py::test_cross_links_the_other_document` |
| Apple 표준 EULA (미정 9) | **결정: Apple 표준 EULA 유지** — 커스텀 라이선스 조건이 없고 ASC 에 별도 입력이 필요 없다. 약관이 링크만 둔다 | `terms#eula` | `tests/test_legal_pages.py::test_terms_marks_eula_choice_as_pending` |
| Google Play 구독 정책 | 가격·결제 주기·자동 갱신·해지 경로(Google Play > 구독) | `terms#subscription` | `test_terms_ko_has_the_required_phrases[Google Play]` |
| Google Play 구독 정책 | 환불은 스토어 정책에 따름 | `terms#withdrawal` | `test_terms_ko_has_the_required_phrases[환불]` |

## 5. 해외 사용자 최소 고지 (미정 23)

**결정: 포함한다.** 영문 스토어에 같은 앱을 내고(ko/en 두 문서), 광고 SDK 가 EU·영국·
캘리포니아 이용자의 개인정보를 처리할 수 있다. 전면적인 GDPR/CCPA 대응(DPO 지정·
대리인·DSAR 절차)은 이 서비스 규모에서 과하므로, **짧은 "해외 사용자" 절 1개** 를
ko/en 양쪽에 둔다 — 처리의 법적 근거, 권리, 감독기관 신고권, "판매·공유하지 않음" 까지.

| 근거(조문·정책) | 요구 내용 | 문서·절 id | 확인 테스트 |
|---|---|---|---|
| GDPR Art.13(1)(c)·6(1)(b)(f) / UK GDPR | 처리의 법적 근거(계약 이행·정당한 이익) | `privacy#international-users` | `test_privacy_ko_has_the_required_phrases[법적 근거]` |
| GDPR Art.15~21 | 열람·정정·삭제·처리 제한·이동·반대 권리 | `privacy#international-users` | `test_every_checklist_section_id_exists_in_both_languages` |
| GDPR Art.77 | 감독기관에 민원을 제기할 권리 | `privacy#international-users` | `test_privacy_en_has_the_required_phrases[supervisory authority]` |
| CCPA/CPRA §1798.120·1798.100 | 개인정보를 판매·공유하지 않음 + 열람·삭제 권리 | `privacy#international-users` | `test_privacy_en_has_the_required_phrases[do not sell]` |

## 6. 사람 결정이 남은 항목 (미정 21·22)

사업자 정보 값은 **설정값(`LEGAL_*`)으로만** 들어간다 — 코드·템플릿·문서에 상호·
등록번호·주소를 적지 않는다(`tests/test_legal_pages.py::test_business_info_values_are_not_hardcoded`,
`tests/test_legal_checklist.py::test_repo_has_no_business_registration_number`). 공개 범위는
**값 자체를 사람이 축약해 넣어** 정한다(코드가 주소를 자르지 않는다).

| 항목 | 결정 | 현재 구현 | 남은 사람 작업 |
|---|---|---|---|
| 사업장 주소(자택) 공개 범위 | **(b) 시·구까지만 + "상세 주소는 요청 시 이메일로 제공"** (사용자, 2026-10-14) | `LEGAL_BUSINESS_ADDRESS` — 비면 미표시. 값이 있으면 조각이 안내 문구를 함께 렌더 | 축약 주소를 prod `.env` 에 넣기. **축약 표시가 전상법 §10①2 를 충족하는지, 애초에 운영자가 "통신판매업자" 인지는 전문가 확인 항목** (`docs/RELEASE.md` "### 16.") |
| 공개용 전화번호 | **(b) 설정값 자리만 두고 사람이 채움** (사용자, 2026-10-14) | `LEGAL_BUSINESS_PHONE` — 비면 그 행을 렌더하지 않음 | 공개용 번호 확보 후 `.env` 에 넣기 |
| 보호책임자 표기 | **(b) 직책 "운영자" + 이메일** (사용자, 2026-10-14) | `privacy#officer` 가 직책·이메일을 적고, `LEGAL_PRIVACY_OFFICER` 를 채우면 성명도 표시 | 성명 공개로 바꾸려면 `.env` 만 수정 |
| 통신판매업 신고 대상 여부 | 미정 22 — 사람 판단 | `LEGAL_MAIL_ORDER_REG_NO` — 비면 행 자체를 렌더하지 않음 | 면제 기준 확인 → 신고 시 `.env` 에 신고번호 |

## 7. 절 id 목록 (ko·en 동일)

| 문서 | 절 id (순서대로) |
|---|---|
| `/privacy` | `general`, `purposes`, `collection`, `third-parties`, `processors`, `overseas`, `destruction`, `rights`, `security`, `automatic-collection`, `children`, `officer`, `remedies`, `international-users`, `changes`, `business-info` |
| `/terms` | `service`, `account`, `subscription`, `withdrawal`, `eula`, `rules`, `service-changes`, `liability`, `privacy`, `terms-changes`, `governing-law`, `business-info` |

순서는 개인정보보호위원회 "개인정보 처리방침 작성지침" 의 권장 구성(총칙 → 목적 →
항목·기간 → 제3자·위탁·국외 이전 → 파기 → 권리 → 안전조치 → 자동 수집 장치 →
14세 → 책임자·창구·구제 → 변경)을 따른다.

## 8. 고지 문장의 구현 근거 (수정 라운드 1, 2026-10-14)

최종 리뷰(`review/impl-review-16.md` D-16-1~3)가 "구현하지 않은 조치를 고지했다" 를 잡아서,
**방침의 보호조치·보유 기간 문장이 어느 코드·설정에 근거하는지** 를 여기에 고정한다. 원칙:
방침은 현행 구현만 적는다. 16 은 "법이 요구하는데 아직 안 하는 조치" 를 코드로 만들지 않고
사람 체크박스로 남겼고, **티켓 36 이 그 두 건(백업 덤프 암호화·접속기록 보관·점검)을
구현해서** 아래 두 행이 "미구현" 에서 "구현됨" 으로 바뀌었다(2026-10-14, 사용자 결정
"필요할 수 있는 것이니 다 만들자"). 없는 기능을 거부 수단으로 안내하던 문구(D-16-5 의
"연결 해제")도 같은 티켓에서 사실대로 고쳤다 —
`tests/test_legal_pages.py::test_privacy_does_not_offer_an_unlink_feature_that_does_not_exist`.

| 방침 문장(절) | 근거 코드·설정 | 상태 |
|---|---|---|
| 백업본은 **압축·암호화한** 덤프 파일째로 14일 뒤 삭제, 덤프는 공개키로 암호화해 저장하고 복호화 키는 서버에 없다 (`privacy#destruction`) | `scripts/backup.sh`(`mysqldump \| gzip -c \| openssl cms -encrypt`, `BACKUP_ENCRYPTION_CERT_FILE`, `BACKUP_RETENTION_DAYS` 보존 삭제), `scripts/restore.sh`(`BACKUP_DECRYPTION_KEY_FILE`), `docker-compose.prod.yml` backup 서비스 | 구현됨 (티켓 36, `tests/test_legal_checklist.py::test_the_backup_script_encrypts_the_dump_with_a_public_key`, `tests/test_backup_restore.py::test_the_dump_on_disk_is_not_readable_without_the_private_key`) |
| 개인정보 처리 행위의 접속기록을 DB 에, 그 밖의 모든 요청을 접근 로그 파일에 남기고 **1년 보관 후 자동 삭제·월 1회 점검·해시 체인으로 위변조 검출** (`privacy#collection`, `privacy#security`) | `app/access_log.py`(기록 지점), `app/models/access_log.py`·`app/repositories/access_log_repository.py`(INSERT 전용·해시 체인), `app/services/access_log_service.py`(검증·만료 삭제·월 점검), `app/cli.py`(`flask access-log verify\|report`), `gunicorn.conf.py`(`${LOG_DIR}/access.log`), `scripts/rotate-access-log.sh`, `ACCESS_LOG_RETENTION_DAYS`(기본 365 = 고시 §8① 최소 기간) | 구현됨 (티켓 36, `tests/test_access_log.py`, `tests/test_access_log_file.py`, `tests/test_legal_checklist.py::test_the_production_entrypoint_configures_an_access_log`) |
| Sentry 에 요청 본문·쿼리스트링·쿠키·IP·사용자 식별자를 보내지 않는다 (`privacy#collection`) | `app/observability.py` `SENTRY_DATA_COLLECTION` | 구현됨 (`tests/test_sentry.py`) |
| 애플 refresh token 은 암호화 저장하고 철회 실패 시 최대 7일 후 폐기 (`privacy#destruction`) | `app/utils/secret_crypto.py`, `app/services/apple_revocation_service.py`, `app/models/apple_revocation_retry.py` | 구현됨 (`tests/test_secret_crypto.py`, `tests/test_apple_revocation.py`) |
| 로그인은 계정을 연결하지 않으면 이전이 없지만, **구독 검증은 계정 연결과 무관하게** 구매 토큰·거래 ID 가 스토어로 전송된다 (`privacy#overseas`) | `app/api/subscriptions.py`(`@with_guest` — 게스트 인증만), `app/services/subscription_service.py`(`verify_receipt` 가 연결 계정 여부와 무관하게 스토어 클라이언트 호출) | 구현 동작과 일치 (`tests/test_subscription_verify.py::test_verify_reaches_the_store_without_a_linked_account`, `tests/test_legal_pages.py::test_store_rows_separate_sign_in_from_subscription_verification`) |

## 9. 스토어 라벨 (티켓 35 — ASC 개인정보 라벨 · Play 데이터 보안 대조)

스토어 두 곳에 같은 사실을 또 적어야 한다: **ASC 개인정보 라벨**
(`mobile/ios/fastlane/app_privacy_details.json`, `asc-submit.yml` 이 올린다)과
**Play 데이터 보안**(`docs/play-data-safety.md`, 콘솔 입력은 사람). 둘의 기준은
방침 `privacy#collection`(수집 항목)과 `privacy#overseas`(국외 이전 받는 자)다 —
방침에 없는 걸 스토어에 신고하면 거짓이고, 방침에 있는 걸 빼면 심사 반려다.

아래 표가 그 1:1 대조이고 `tests/test_store_labels.py` 가 세 곳이 어긋나면 깨진다.
"공유" 는 Play 기준의 제3자 전송 = 방침 `#overseas` 에 받는 자가 있는 항목이다.

| 방침 `#collection` 항목 | ASC category | Play 데이터 유형 | 공유(받는 자) |
|---|---|---|---|
| 게스트 토큰 | `USER_ID` | 개인 정보 > 사용자 ID | 없음 |
| 계정 이메일 | `EMAIL_ADDRESS` | 개인 정보 > 이메일 주소 | 없음 |
| 애플 refresh token | `OTHER_DATA_TYPES` | 개인 정보 > 기타 정보 | Apple |
| 시도 기록 | `GAMEPLAY_CONTENT` | 앱 활동 > 기타 사용자 제작 콘텐츠 | 없음 |
| 오늘의 순위 | `GAMEPLAY_CONTENT` | 앱 활동 > 기타 사용자 제작 콘텐츠 | 없음 |
| 구독 식별자 | `PURCHASE_HISTORY` | 금융 정보 > 구매 내역 | Google, Apple |
| 광고 ID | `DEVICE_ID` | 기기 또는 기타 ID | AdMob |
| 광고 ID(노출·클릭 측정) | `ADVERTISING_DATA` | 앱 활동 > 앱 내 상호작용 | AdMob |
| 앱 사용 이벤트 | `PRODUCT_INTERACTION` | 앱 활동 > 앱 내 상호작용 | Firebase |
| 접속·오류 기록(Sentry 오류) | `CRASH_DATA` | 앱 정보 및 성능 > 비정상 종료 로그 | Sentry |
| 접속·오류 기록(Sentry 성능) | `PERFORMANCE_DATA` | 앱 정보 및 성능 > 진단 | Sentry |
| 접속·오류 기록(접속기록·접근 로그) | `OTHER_DIAGNOSTIC_DATA` | 앱 정보 및 성능 > 기타 앱 성능 데이터 | 없음 |

### 대조에서 찾은 차이 2건 (둘 다 티켓 35 에서 고쳤다)

| 차이 | 왜 생겼나 | 어떻게 고쳤나 |
|---|---|---|
| **애플 refresh token 이 ASC 라벨에 없었다** | 티켓 34 는 "ASC 범주에 대응 항목이 없고 `USER_ID` 와 같은 축" 으로 보고 행을 만들지 않았다(`review/impl-evidence-34.md` §7) | ASC 에는 그 자리가 있다 — **"기타 데이터"(`OTHER_DATA_TYPES`)**. 방침 `#collection`·`#overseas`(애플 행)가 이미 "보관하고 철회 때 Apple 로 보낸다" 고 적고 있어 신고 대상이다. `OTHER_DATA_TYPES` / `APP_FUNCTIONALITY` / `DATA_LINKED_TO_YOU` 로 넣었다 |
| **접속기록이 ASC 라벨에 없었다** | 34 당시 방침의 "접속·오류 기록" 은 Sentry 뿐이었고, DB 접속기록·접근 로그 파일은 **그 뒤 티켓 36** 이 만들었다. 34 의 라벨(`CRASH_DATA`·`PERFORMANCE_DATA`, 둘 다 `NOT_LINKED`)은 36 이 늘린 수집을 모른다 | **`OTHER_DIAGNOSTIC_DATA`** 를 더했다. Sentry 와 달리 행위자(`guest.<id>` / 가린 운영자 이메일)와 원격 IP 가 남아 **`DATA_LINKED_TO_YOU`** 다. Sentry 두 행은 그대로 `NOT_LINKED`(요청 본문·IP·식별자를 보내지 않는다 — `app/observability.py`) |

### 대조에서 찾은 차이 3번 — 고치지 않고 남긴 것

| 차이 | 사실 | 왜 여기서 안 고쳤나 |
|---|---|---|
| **"앱 사용 이벤트"(Firebase Analytics)가 방침 `#collection` 의 항목 목록에 없다** | 방침은 이 전송을 `#overseas` 의 Firebase 행(앱 인스턴스 식별자·이벤트 4개)에만 적고, 3절 "수집하는 정보와 보유 기간" 의 `<dt>` 목록에는 두지 않았다. 스토어 두 곳에는 신고한다(`PRODUCT_INTERACTION` / 앱 활동 > 앱 내 상호작용) — 실제로 전송하므로 빼면 거짓 신고가 된다 | 스토어 라벨이 아니라 **법적 문서 본문**을 고치는 일이다(개보법 §30①3 "처리하는 개인정보의 항목"). 문서 구조·ko/en 동기화·테스트는 티켓 16 이 들고 있어서, 티켓 35 가 한쪽 언어만 건드리면 `tests/test_legal_checklist.py` 의 구조 테스트와 충돌한다. **사람 확인 항목**으로 `docs/RELEASE.md` "### 35." 에 두고, `tests/test_store_labels.py` 는 대조 기준을 "수집 항목 + 국외 이전" 으로 두어 지금 상태를 사실대로 지킨다 |

### 같이 확인한 것

- **privacy/support URL**: 스토어 메타데이터의 두 URL 은 `/privacy`·`/terms` 다
  (`mobile/ios/fastlane/metadata/*/privacy_url.txt`·`support_url.txt`). 방침·약관이
  ko/en 양쪽에 있어 스토어 언어별로 따로 둘 필요가 없다(쿼리 `?lang=` 없이 기기
  언어를 따른다).
- **ASC EULA**: 미정 9 의 결정(§4 표) 그대로 **Apple 표준 EULA 를 쓰고 ASC 에 아무
  것도 입력하지 않는다**. 약관 `terms#eula` 가 링크만 둔다.
- **Play 패밀리 정책·독립 보안 검토**: 둘 다 "아니요" 다(`docs/play-data-safety.md` §1).
  받지 않은 검토를 받았다고 적지 않는다.
