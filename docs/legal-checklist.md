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
| 개보법 §30①4 / 시행령 §31①2 | 개인정보의 파기 절차·방법 | `privacy#destruction` | `test_privacy_ko_has_the_required_phrases[파기]` |
| 개보법 §30①5 / §35~§37 | 정보주체와 법정대리인의 권리·의무와 행사 방법 | `privacy#rights` | `test_delete_page_is_linked_from_the_rights_section` |
| 개보법 §29 / 시행령 §30 | 안전성 확보 조치(암호화·접근 통제·접속기록) | `privacy#security` | `test_every_checklist_section_id_exists_in_both_languages` |
| 개보법 §30①6 / §31 / 시행령 §32 | 개인정보 보호책임자의 **성명 또는 직책**·연락처 — **사용자 결정(2026-10-14): 직책 "운영자" + 이메일**(성명은 `LEGAL_PRIVACY_OFFICER` 를 채우면 표시) | `privacy#officer` | `test_privacy_ko_has_the_required_phrases[개인정보 보호책임자]` |
| 시행령 §31①3 | 열람 청구를 접수·처리하는 부서(창구) | `privacy#officer` | `test_privacy_ko_has_the_required_phrases[열람]` |
| 시행령 §31①4 / §63 | 권익 침해 구제 방법 — 개인정보침해신고센터(118), 개인정보 분쟁조정위원회(1833-6972) | `privacy#remedies` | `test_privacy_ko_has_the_required_phrases[118]`, `[1833-6972]` |
| 개보법 §30①7 / 시행령 §31①6 | 자동 수집 장치의 설치·운영과 거부 방법 — 쿠키(세션), 광고 식별자(IDFA/ADID), 분석 SDK | `privacy#automatic-collection` | `test_privacy_ko_has_the_required_phrases[광고 ID 초기화]`, `[쿠키]` |
| 개보법 §22의2 | 만 14세 미만 아동의 개인정보 처리(동의·미수집) | `privacy#children` | `test_privacy_ko_has_the_required_phrases[만 14세]` |
| 시행령 §31①5 / §31② | 처리방침 변경 시 시행일·변경 내용·고지 방법, 이전 버전 확인 방법 | `privacy#changes` | `test_privacy_ko_has_the_required_phrases[시행일]` |
| 개보법 §30①7의2 / §37의2 | 가명정보 처리·자동화된 결정 — **해당 없음** 을 명시 | `privacy#general` | `test_every_checklist_section_id_exists_in_both_languages` |

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
| 개보법 §28의8②5 | 이전 거부 방법·절차와 **거부의 효과**(거부 수단이 없는 기능은 "서비스를 쓰지 않는 것" 뿐임을 명시) | `privacy#overseas` | `test_privacy_ko_has_the_required_phrases[이전을 거부]`, `tests/test_legal_pages.py::test_transfer_section_ko_states_real_opt_outs` |

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
