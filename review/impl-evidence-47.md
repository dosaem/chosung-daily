# 티켓 47 증거 — 개인정보처리방침: 기기 보안 저장소(iOS 키체인) 식별자 보관 고지

- 대상: 로컬 `main`(`547cee5`) 위의 worktree `dosaem/t47-privacy-keychain`.
- 범위: 브리프의 5개 항목 — ① 코드에서 실제 동작 확인 ② 방침 ko·en 수정(+ 체크리스트·
  법적 문서 테스트 갱신) ③ 시행일 ④ `docs/RELEASE.md` 항목 ⑤ 앱 내 안내 판단.
- push·NAS·배포·외부 호출·계정/결제/인증 정보 입력·시크릿 기록·하위 워커: 하지 않았다.
- **기능 변경 없음** — 바뀐 것은 방침 문안(ko·en), 앱 문구 한 문장, 문서 4개, 테스트다.

## 0. 한 줄 요약

전체 pytest **1764개 통과** · `flutter test` **796개 통과** · `ruff check`·`flutter analyze`·
`dart format` 0건 · `impeccable detect` 10개 조합 전부 0건이다.
앱이 게스트 토큰을 어디에 두고 iOS 는 앱을 지워도 남는다는 사실을 **코드에서 먼저 확인한
뒤** 개인정보처리방침 ko·en 네 절(`#collection`·`#automatic-collection`·`#destruction`·
`#rights`)에 사실대로 넣었고, 그 고지를 구현에 묶는 테스트 4개(파라미터 포함 6개)와 필수
문구 2개를 더했다. `LEGAL_EFFECTIVE_DATE` 를 2026-10-16 으로 올리고 `docs/RELEASE.md` 의
"방침에 추가 필요" 칸을 "반영됨(티켓 47) — 운영자 최종 확인" 으로 바꿨다. 앱 안내는 계정
삭제 확인 시트 문구에 한 문장만 더했다(새 키·새 위젯 없음).

## 1. 코드에서 확인한 사실 — 문안은 이것만 적는다

| 무엇 | 확인한 사실 | 근거 파일 |
|---|---|---|
| 게스트 토큰 저장소 | `flutter_secure_storage` 11.2 → **iOS 키체인 / Android EncryptedSharedPreferences**, `IOSOptions(accessibility: KeychainAccessibility.first_unlock)` | `mobile/lib/guest/guest_token_store.dart:12,34-35` · `mobile/pubspec.yaml:27` |
| 같은 저장소의 다른 값 | 기기 플래그(`link_account_notice_seen`) — 값은 `'1'` 하나, 서버로 가지 않는다 | `mobile/lib/local/local_flags.dart:43-66` |
| **같은 저장소가 아닌** 값 | 온보딩 완료 플래그는 `shared_preferences`(iOS NSUserDefaults) — 주석이 이유를 "키체인은 앱을 지워도 남아서" 로 적어 둔다 | `mobile/lib/onboarding/onboarding_store.dart:12-17` |
| iOS: 앱 삭제 후 존속 | 키체인 항목은 앱 삭제 후에도 남아 재설치 시 같은 토큰이 돌아온다 → 기록이 이어진다. **의도된 동작**(사용자 결정 2026-10-16) | `docs/RELEASE.md` "### 46." · 위 온보딩 주석 |
| Android: 앱과 함께 소멸 | EncryptedSharedPreferences 는 앱 데이터다. 매니페스트에 `allowBackup`·`dataExtractionRules`·`fullBackupContent` 선언이 **없다**(기본 자동 백업). 자동 백업이 파일을 되살려도 복호화 키는 Keystore 에 있어 함께 백업되지 않으므로 식별자는 살아 돌아오지 않는다 | `mobile/android/app/src/main/AndroidManifest.xml`(해당 속성 grep 0건) |
| 계정 삭제가 하는 일(앱) | `DELETE /me` → `clearPerAccount()` → `POST /guests` 로 **새 토큰을 받아** `replaceWith` 가 저장소에 **덮어쓴다**. 지우고 비워 두는 경로가 아니다 | `mobile/lib/account/account_controller.dart:115-141` · `mobile/lib/guest/guest_token_provider.dart:16-20` |
| 서버 쪽 삭제 범위 | 시도 기록·연속 기록·연결 계정·구독 식별자·힌트 기록·게스트 토큰 + 오늘 리더보드 등록분(방침 `#destruction` 이 이미 적는 그대로) | 기존 방침 본문 · `app/services/account_deletion_service.py` |
| 웹 | 토큰은 `localStorage` 의 `chosung_token` — 방침 `#automatic-collection` 쿠키 항목에 이미 있었다 | `web/static/app.js:2,199,223,1054` |

**그래서 "지우는 법" 을 "기기 식별자를 제거한다" 로 쓰지 않았다.** 구현은 새 토큰으로
**교체**한다(앱은 토큰 없이 돌지 않는다). 방침은 "새로 발급한 토큰으로 바뀌어 지운 기록으로
돌아갈 수 없습니다" 로 적었다 — 과장도 축소도 아닌 그대로다.

웹 `/account/delete` 로 지우면 서버 기록은 사라지지만 **앱 키체인의 죽은 토큰은 그대로
남는다**. 그래서 교체 문장의 주어를 "앱에서 지우면" 으로 한정했다.

## 2. 고친 자리

### 2.1 개인정보처리방침 (ko·en 두 벌, 같은 커밋)

`web/templates/legal/privacy.ko.html` · `privacy.en.html`

| 절 | 무엇을 더했나 |
|---|---|
| `#collection` "게스트 토큰" | 무작위 값이고 개인 식별 정보가 아니라는 점 · 왜 쓰는지(회원가입·로그인 없이 기록 유지) · 웹/앱 저장 위치(localStorage / 기기 보안 저장소 = iOS 키체인·Android 암호화 저장소) · iOS 는 앱을 지워도 남아 재설치 시 이어진다 · 10절 참조 |
| `#automatic-collection` | 제목에 "기기 저장소" 를 넣고, 쿠키 다음에 **새 항목 "기기 보안 저장소 (앱의 게스트 토큰)"** 를 뒀다 — 무엇·어디·왜·서버로 가는 값은 토큰뿐·iOS 존속(Android 는 앱과 함께 소멸)·지우는 법(앱을 지우기 **전에** 계정 삭제 또는 웹 삭제 페이지)·"앱을 지우는 것만으로는 서버의 기록도, iOS 키체인의 토큰도 지워지지 않습니다". 쿠키 항목의 localStorage 설명이 앱까지 덮는 것처럼 읽히지 않게 새 항목을 가리키게 했다 |
| `#destruction` 절차 | 앱에서 삭제하면 같은 자리에서 기기 보안 저장소의 토큰도 새 토큰으로 바뀐다는 한 문장 |
| `#rights` 삭제 항목 | "**앱을 지우는 것만으로는 지워지지 않습니다**" — 권리 행사 절에서도 찾을 수 있게 |

절을 **새로 만들지 않았다** — 기존 `tests/test_legal_checklist.py` 의
`test_rendered_section_ids_are_all_in_the_checklist` ·
`test_section_ids_match_in_order_across_languages` 가 그대로 통과한다. 절 id·순서는 ko·en 동일.

### 2.2 시행일

`app/web.py:21` `LEGAL_EFFECTIVE_DATE = date(2026, 10, 14)` → `date(2026, 10, 16)`.
개정 이력 목록은 이 문서에 없다(`#changes` 는 "시행일 갱신 + 시행 7일 전부터 변경 내용 게시"
방식이고, README "법적 문서" 절도 시행일만 가리킨다) — 그래서 날짜만 올렸다.

### 2.3 앱 안내 — 한 문장, 새 키 없음

`mobile/assets/translations/{ko,en}.json` 의 `account.delete_body`(계정 삭제 확인 시트,
`mobile/lib/widgets/delete_account_dialog.dart` 가 그린다):

- ko: "… 되돌릴 수 없어요. **이 기기에 저장된 식별자도 새 값으로 바뀌어서, 앱을 지웠다 다시
  깔아도 이 기록으로 돌아올 수 없어요.** 구독 중이면 …"
- en: "… cannot be restored. **The identifier stored on this device is replaced with a new one,
  so reinstalling the app will not bring this record back.** If you are subscribed, …"

이 문구를 **전문(全文)으로 고정하던 테스트**가 하나 있어 같이 고쳤다 —
`mobile/test/screens/records_account_test.dart` 의 "다이얼로그에 되돌릴 수 없음과 구독 별도
해지가 적혀 있다". 전체 `flutter test` 에서 1건 실패로 나타났고(단독 실행으로는 재현되지
않아 HEAD 번역으로 되돌린 대조 실행 796/796 통과 → 내 변경이 원인임을 확인한 뒤 잡았다),
새 문장을 포함한 전문으로 바꾸고 테스트 이름을 "되돌릴 수 없음·**기기 식별자 교체**·구독
별도 해지" 로 고쳤다. 문구가 다시 빠지면 이 테스트가 깨진다.

**판단: 설정 목록에는 줄을 더하지 않았다.** 이유 — ① 삭제 시점의 결정에 필요한 사실은 확인
시트가 가장 잘 닿는 자리고, ② 저장 방식 전체 설명은 설정에 이미 있는 "개인정보처리방침" 행
(`records.privacy` → `/privacy` 10절)이 담당하며, ③ "내 기록" 화면에는 골든 스냅샷
(`records_light_390.png`·`records_linked_390.png`·`records_notification_off_390.png`·
`records_tablet_1024.png`)이 걸려 있어 줄을 더하면 디자인 변경이 된다 — 이 티켓은 기능·디자인
변경 금지다. 새 번역 키를 만들지 않고 기존 문구를 늘린 것도 같은 이유다.

### 2.4 문서

- `docs/legal-checklist.md`: §30①7 / 시행령 §31①6 행에 "브라우저 localStorage, **기기 보안
  저장소**(앱의 게스트 토큰 — iOS 키체인·Android 암호화 저장소)" 를 넣고 확인 테스트에
  `[기기 보안 저장소]` 를 더했다. 그 아래에 **새 행**(§30①2·3 / 시행령 §31①1, 저장 위치·존속)
  을 만들어 네 절과 새 테스트 4개를 묶었다.
- `docs/RELEASE.md`: "### 16." 의 "방침에 추가 필요 …" 체크박스를 "**반영됨(티켓 47) — 운영자
  최종 확인** …" 으로 바꿨고(운영자 확인이 남아 열린 칸으로 둔다), "### 46." 끝에 "→ 티켓 47
  에서 넣었다" 를 적고 **"### 47."** 절을 새로 썼다 — §1 의 사실 표, 고친 자리, 운영자가 할 일.
  "### 46." 의 "빠져 있는 것" 단락은 "빠져 있던 것 …(아래 설명은 티켓 46 시점의 상태다 —
  티켓 47 이 전부 채웠다)" 로 바꿔, 이미 해결된 서술이 현재형으로 남지 않게 했다.
- `README.md` "법적 문서" 절의 **갱신 트리거** 목록에 "앱이 게스트 토큰을 두는 자리가 바뀔
  때" 한 줄 — 저장소를 바꾸면 방침의 그 문장이 거짓이 되고, `tests/test_legal_checklist.py`
  가 먼저 깨진다는 것까지 적었다.
- `docs/play-data-safety.md`: "게스트 토큰" 행 비고에 저장 위치와 iOS 존속을 적었다. **수집·
  공유·필수/선택·목적 칸은 그대로다** — 기기 안 저장은 Play Data safety 의 신고 항목이 아니고,
  `tests/test_store_labels.py` 의 대조 단정도 그대로 통과한다.

### 2.5 테스트 — 고지를 구현에 묶는다

`tests/test_legal_checklist.py`

| 테스트 | 무엇이 깨지면 실패하나 |
|---|---|
| 필수 문구 `기기 보안 저장소` / `device secure storage` | 방침에서 그 공시가 사라지면 |
| `test_privacy_discloses_the_app_device_secure_storage[ko,en]` | 자동 수집 절에서 저장 위치·iOS 존속·지우는 법 문구가 빠지면. **과장 금지 쪽도 본다** — "앱을 지우면 함께 지워집니다"/"deleting the app removes it" 같은 반대 주장, "키체인에서 직접 지울 수" 같은 없는 수단이 들어오면 실패 |
| `test_rights_section_says_deleting_the_app_is_not_deletion[ko,en]` | 권리 행사 절에서 "앱 삭제 ≠ 삭제" 가 사라지면 |
| `test_the_app_still_keeps_the_guest_token_in_the_platform_secure_storage` | 토큰 저장소를 `flutter_secure_storage` 아닌 것으로 바꾸면(= "기기 보안 저장소"·"iOS 는 남는다" 가 거짓이 된다). 온보딩 플래그가 반대로 보안 저장소로 옮겨가도 실패 |
| `test_app_deletion_replaces_the_stored_guest_token` | 앱의 계정 삭제가 새 토큰을 받아 덮어쓰지 않게 되면(= `#destruction`·10절의 교체 문장이 거짓이 된다) |

`mobile/test/screens/records_account_test.dart` 의 삭제 다이얼로그 문구 테스트는 §2.3 에
적은 대로 새 문장을 포함하게 고쳤다.

문구 단정은 줄바꿈에 걸친 문장을 놓치지 않게 공백을 한 칸으로 줄여 비교한다(첫 실행에서
en `android encrypted storage` 가 템플릿 줄바꿈에 걸려 실패했다 — 숨기지 않고 적는다).

## 3. 검증

공통 자원: `TEST_DATABASE_URL=…/chosung_daily_test_t47`(+`_migrations`),
`TEST_REDIS_URL=redis://localhost:6379/7`.

### 3.1 `ruff` · 전체 `pytest`

```
$ uv run ruff check .
All checks passed!                                               ← exit 0 (CI ci.yml:56)

$ TEST_DATABASE_URL=…/chosung_daily_test_t47 TEST_REDIS_URL=…/7 \
    uv run pytest -q -p no:cacheprovider
1764 passed in 1067.86s (0:17:47)                                ← exit 0
```

이 1764개 실행은 **문구·문서·테스트를 전부 확정한 뒤** 돌린 것이다. 중간에 한 번 돌리다
문구를 더 고쳤으므로 그 실행은 버리고(고아 pytest 가 테스트 DB 를 잡지 않도록 프로세스까지
확인해 정리했다) 처음부터 다시 돌렸다 — 섞인 상태의 숫자를 적지 않으려는 것이다.
`ruff format` 은 CI 에 없어(`ci.yml` 은 `ruff check` 만 돌린다) 기준으로 삼지 않았다.

### 3.2 `flutter analyze` · `dart format` · `flutter test`

```
$ cd mobile && flutter analyze
No issues found! (ran in 2.9s)                                   ← exit 0 (info 포함 0건)

$ dart format --set-exit-if-changed lib test integration_test test_driver
Formatted 201 files (0 changed) in 0.52 seconds.                 ← exit 0 (CI flutter-ci.yml:45)

$ flutter test
00:58 +796: All tests passed!                                    ← exit 0
```

**중간에 1건 실패했고 고쳤다**(숨기지 않고 적는다): `account.delete_body` 를 늘리자
`test/screens/records_account_test.dart` 의 문구 전문 단정이 깨졌다 — 단독 실행으로는
재현되지 않아, 번역 두 파일만 HEAD 로 되돌린 **대조 실행(796/796 통과)** 으로 내 변경이
원인임을 확인한 뒤 단정과 테스트 이름을 새 문구에 맞췄다(§2.3).

### 3.3 `impeccable detect` — 0건

Jinja 템플릿을 직접 주면 `url_for` 를 못 풀어 CSS 를 못 읽으므로(티켓 01·09·16 메모)
개발 서버를 띄워 **URL 로** 돌렸다. 바이너리: `~/.impeccable/bin/0.1.14/impeccable`.

```
$ FLASK_ENV=testing uv run flask --app wsgi run --port 5147     # (백그라운드)

$ impeccable detect "http://127.0.0.1:5147/privacy?lang=ko"   → (출력 없음) exit=0
$ impeccable detect "http://127.0.0.1:5147/privacy?lang=en"   → (출력 없음) exit=0
$ impeccable detect "http://127.0.0.1:5147/terms?lang=ko"     → (출력 없음) exit=0   (회귀)
$ impeccable detect "http://127.0.0.1:5147/terms?lang=en"     → (출력 없음) exit=0   (회귀)

$ impeccable detect --viewport {390x844,320x844,1280x900} "…/privacy?lang={ko,en}"
  6개 조합 전부 → (출력 없음) exit=0
```

티켓 16 이 같은 페이지에서 `em-dash-overuse` advisory 를 한 번 맞았으므로(ko 본문 줄표
20개 → 6개로 줄였던 이력) 줄표를 더한 뒤 세 뷰포트로 다시 확인했다 — 0건이다. 위 10개
조합은 **문구를 최종 확정한 뒤** 다시 돌린 값이다(en 단락 줄바꿈 정리·ko 조사 수정 이후).
`/account/delete` 는 이 티켓에서 바꾸지 않아 돌리지 않았다.

## 4. 사람(운영자)이 할 일 — 1건

`docs/RELEASE.md` "### 16." 의 그 칸이다: **`/privacy?lang=ko`·`?lang=en` 의 3절과 10절을
읽고 문안을 승낙한다.** 사실과 다른 문장이 보이면 그 문장만 고치고 `LEGAL_EFFECTIVE_DATE` 를
다시 올린다. 문안은 운영자가 "좋다고 판단되는 문구로 직접 넣어라" 고 위임한 범위에서 썼고,
§1 의 확인 사실만 담았다.

## 5. 남긴 것 · 적어만 둔 것

- **개정 이력 목록은 만들지 않았다.** `#changes` 는 "시행일 갱신 + 시행 7일 전부터 변경 내용
  게시" 방식이고 레포에 이력 목록 자리가 없다. 만들면 새 절이 되어 체크리스트 표와 `#changes`
  문장까지 같이 고쳐야 하는 별건이라, 날짜만 올렸다.
- **Android 자동 백업은 방침에 쓰지 않았다.** "Android 는 앱을 지우면 함께 사라집니다" 까지만
  적었다 — 복원되더라도 Keystore 키가 함께 백업되지 않아 읽을 수 없다는 세부는 §1 표에만 두고,
  방침에는 결과만 적는 쪽을 골랐다(과장도 축소도 아니다).
- 테스트 DB `chosung_daily_test_t47`(+`_migrations`)는 레포 관례대로 **남겨 뒀다**.

## 6. 테스트 자원

- MySQL: `chosung_daily_test_t47` · `chosung_daily_test_t47_migrations` (worktree 전용).
- Redis: pytest `7`.
- Flask 개발 서버: 포트 `5147` (detect 용, 확인 후 종료).
