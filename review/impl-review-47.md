# 티켓 47 최종 리뷰 — 개인정보처리방침: 기기 보안 저장소(iOS 키체인) 식별자 보관 고지

- 라운드: 1 (첫 리뷰)
- 대상: `dosaem/t47-privacy-keychain` = 로컬 `main`(`547cee5`) + 1 커밋 `573138f`
  `docs(legal): 기기 보안 저장소(iOS 키체인) 게스트 토큰 보관 고지 — 티켓 47`. 리뷰 시작 시 트리 clean.
- 읽은 것: 티켓 원문, `.scratch/store-launch/spec.md`(§15 법적 문서·US 45a), `git diff main...HEAD`,
  `review/impl-evidence-47.md`, 방침 ko·en 본문 전체, `mobile/lib/guest/*`·`local/local_flags.dart`·
  `onboarding/onboarding_store.dart`·`account/account_controller.dart`, `flutter_secure_storage` 11.2.0
  Android 소스(pub cache), `docs/legal-checklist.md`, `tests/test_legal_checklist.py` 전체.
- 바뀐 파일 12개 — 애플리케이션 로직 변경 없음(`app/web.py` 는 날짜 상수 1줄). UI 변경은 방침 본문
  문구와 앱 다이얼로그 문장 1개뿐이라 디자인 시스템 토큰·레이아웃은 건드리지 않았다.

## 1. 직접 돌린 검증 (증거 문서를 믿지 않고 재실행)

| 항목 | 명령·조건 | 결과 |
|---|---|---|
| ruff | `uv run ruff check .` | All checks passed, exit 0 |
| 전체 pytest | `TEST_DATABASE_URL=…/chosung_daily_test_t47`, `TEST_REDIS_URL=redis://localhost:6379/7`, `uv run pytest -q -p no:cacheprovider` | `1764 passed in 1922.35s (0:32:02)`, exit 0, FAILED/ERROR 0 |
| flutter analyze | `mobile/` `flutter analyze` | No issues found (info 포함 0건), exit 0 |
| dart format | `dart format --set-exit-if-changed lib test integration_test test_driver` | 201 files, 0 changed, exit 0 |
| flutter test | `flutter test` | `+796: All tests passed!`, exit 0 (pytest 와 병렬 실행이라 2분 34초) |
| flutter build apk | — | **돌리지 않았다**: 네이티브 변경 없음(바뀐 mobile 파일은 번역 JSON 2개와 Dart 테스트 1개) |
| impeccable detect | 개발 서버 `:5148`, `~/.impeccable/bin/0.1.14/impeccable detect` — `/privacy?lang=ko`·`?lang=en` × 390x844·1280x900, `/terms?lang=ko`(회귀) | 5개 조합 전부 출력 없음, exit 0 |

## 2. 코드에서 사실 재확인 (방침 문장 ↔ 구현)

| 방침 문장 | 구현 근거 | 판정 |
|---|---|---|
| 게스트 토큰은 개인 식별 정보가 담기지 않은 무작위 값 | `app/models/guest.py:14` `uuid.uuid4()` | 사실 |
| 앱은 토큰을 기기 보안 저장소(iOS 키체인 · Android 암호화 저장소)에 둔다 | `mobile/lib/guest/guest_token_store.dart:13-38` `FlutterSecureStorage`, `IOSOptions(accessibility: first_unlock)` | 사실 |
| "이 안내를 이미 봤다" 같은 기기 표시도 같은 저장소 | `mobile/lib/local/local_flags.dart:47-69` `SecureLocalFlagStore`(값 `'1'`) | 사실 |
| iOS 키체인은 앱을 지워도 남아 재설치 시 같은 토큰이 돌아온다 | 키체인 항목은 앱 삭제와 무관하게 존속(`ThisDeviceOnly` 여부는 iCloud 동기화만 가름). 레포 안 근거 `onboarding_store.dart:14-16` 주석 | 사실 |
| Android 는 앱을 지우면 함께 사라진다 | 플러그인은 앱 전용 SharedPreferences + KeyStore 래핑 키. 자동 백업으로 파일만 복원되면 복호화 실패 → 플러그인이 손상 데이터를 지우고 재시도(`FlutterSecureStorage.java:54-70`, `handleStorageError`). 식별자는 되살아나지 않는다 | 사실(결과 기준) |
| 앱 "계정 삭제" 는 서버 기록 삭제 뒤 기기 토큰을 **새 토큰으로 교체** | `account_controller.dart:115-139` `DELETE /me` → `clearPerAccount()` → `createGuest` → `_adopt` → `replaceWith` (`guest_token_provider.dart:16-20` `_store.write`). Flutter 테스트 `account_controller_test.dart:580-595` 가 `store.token == 'fresh-guest'` 를 실제로 검증 | 사실 — "제거" 가 아니라 "교체" 로 쓴 것이 맞다 |
| 서버 쪽 삭제 범위(시도·연속·연결 계정·구독 식별자·힌트·토큰·오늘 리더보드) | 기존 본문 그대로, 이 티켓이 바꾸지 않음 | 변경 없음 |
| 앱이 여는 문서 = 웹 `/privacy` | `records_tab.dart:326-333` `legalDocumentUrl(LegalDocument.privacy, uiLanguage)` | 같은 문서 |

## 3. 티켓 체크박스별 충족 여부

| # | 요구 | 충족 | 근거 |
|---|---|---|---|
| 1 | 코드에서 실제 동작 먼저 확인, 확인한 사실만 쓴다 | ✅ | 위 §2 — 증거 §1 표의 항목 전부 소스로 재확인. "계정 삭제 = 기기 식별자 제거" 라는 티켓 원문 표현을 구현대로 "새 토큰으로 교체" 로 고쳐 쓴 판단이 맞다 |
| 2 | 방침 ko·en 해당 절에 무엇·어디·왜·iOS 존속·지우는 법 추가, 체크리스트·법적 문서 테스트 갱신 | ✅ | `#collection`(게스트 토큰 항목)·`#automatic-collection`(새 `<dt>` "기기 보안 저장소")·`#destruction`·`#rights` 네 절, ko·en 동일 구조(`<dt>` 23/23, 절 id·순서 일치 테스트 통과). `docs/legal-checklist.md` 2행, `tests/test_legal_checklist.py` 필수 문구 2개 + 테스트 4개(파라미터 6개) |
| 3 | 시행일/개정 이력 규칙대로 갱신 | ✅ | `LEGAL_EFFECTIVE_DATE` 10-14 → 10-16(README 규칙 "본문을 고칠 때 같이 올린다"). 개정 이력 목록은 문서에 없어 만들지 않음 — 타당(참고 P-3) |
| 4 | `docs/RELEASE.md` "방침에 추가 필요" → "반영됨(티켓 47) — 운영자 최종 확인" | ✅ | `docs/RELEASE.md` "### 16." 체크박스 문구 교체 + "### 46." 현재형 서술 정정 + "### 47." 신설 |
| 5 | 앱 내 안내 한 줄 필요 여부 판단, 필요하면 ko/en 키 | ✅ | 계정 삭제 확인 시트 `account.delete_body` 에 ko·en 한 문장. 새 키 대신 기존 키를 늘린 이유(골든 스냅샷·디자인 변경 금지)가 증거 §2.3 에 적혀 있고 타당. 깨진 전문 단정 테스트를 새 문구로 갱신 |
| 제약 | 사실과 다른 문구 금지·기능 변경 금지·범위 밖 변경 없음·시크릿 없음 | ✅ | diff 에 로직 변경 없음. `docs/play-data-safety.md` 비고·README 갱신 트리거 추가는 방침 갱신 책임과 직접 연결돼 범위 안. 시크릿·외부 호출 없음 |

## 4. 결함

BLOCKER 0 · MAJOR 0 · MINOR 2.

### D-47-1 (MINOR) — ko 10절 "서버로 보내는 값은 … 게스트 토큰뿐입니다" 가 앱 전체로 읽힐 수 있다

- 파일: `web/templates/legal/privacy.ko.html:305-307`
- 재현: 독자가 "기기 보안 저장소" 항목을 읽는다 → 기대: "이 저장소의 값 중 서버로 가는 것은 토큰뿐" →
  실제 문장 "로그인 없이 기록을 잇기 위한 것이고, 서버로 보내는 값은 요청을 인증하는 게스트 토큰뿐입니다"
  는 주어가 생략돼 "앱이 서버로 보내는 값은 토큰뿐" 으로도 읽힌다. 앱은 제출 단어·시도 기록·구독
  검증값 등도 보내므로 그 독해로는 축소 고지가 된다. en 은 "the only one of **these values** sent to the
  server" 로 한정돼 있어 문제 없다.
- 고치는 방향: "이 저장소의 값 가운데 서버로 보내는 것은 요청을 인증하는 게스트 토큰뿐입니다" 처럼
  한정어 한 마디. 문구 수정이라 `LEGAL_EFFECTIVE_DATE` 는 같은 날이면 그대로.

### D-47-2 (MINOR) — `test_app_deletion_replaces_the_stored_guest_token` 이 소스 문자열(들여쓰기 포함)을 단정한다

- 파일: `tests/test_legal_checklist.py:369-378`
- 재현: `guest_token_provider.dart` 의 `replaceWith` 본문을 의미 변화 없이 한 줄만 다시 포맷하거나
  주석 한 줄을 끼워 넣는다 → 기대: 동작 불변이므로 통과 → 실제: `"Future<void> replaceWith(String token)
  async {\n    await _store.write(token);"` 정확 일치 단정이 깨진다. 반대로 `write` 를 다른 메서드로
  감싸도 문자열이 남아 있으면 통과한다 — 동작이 아니라 텍스트를 본다. 실제 동작은 Flutter 테스트
  `account_controller_test.dart:580` ("DELETE /me 뒤 새 게스트를 발급받아 갈아끼운다", `store.token ==
  'fresh-guest'`) 가 이미 검증한다.
- 고치는 방향: 파이썬 쪽은 "교체 경로가 존재한다" 수준의 완화된 단정(예: `"_api.createGuest("` ·
  `"_adopt(token)"` 까지만)으로 줄이고, 주석으로 Flutter 테스트 이름을 가리키면 충분하다. 저장소 종류
  테스트(`test_the_app_still_keeps_…`)의 import 단정은 그대로 두어도 된다.

## 5. 참고 (취향·후속, 판정에 영향 없음)

- P-1 `#changes` 는 "시행일 7일 전부터 변경 내용을 적어 둔다" 고 하는데 이번 개정은 시행일 = 수정일이다.
  출시 전(이용자 0)이고 티켓 16·46 도 같은 방식으로 날짜만 올렸으므로 문제 삼지 않는다. 출시 뒤 첫
  개정부터는 7일 규칙을 실제로 지켜야 한다 — RELEASE.md 운영자 할 일에 한 줄 있으면 좋다.
- P-2 Android 자동 백업: 매니페스트에 `allowBackup`/`dataExtractionRules` 선언이 없어 기본 백업이 켜져
  있다. 플러그인 11.2.0 은 복호화 실패 시 손상 데이터를 지우고 재시도하므로 방침 문장은 참이지만, 플러그인
  README 가 `allowBackup="false"` 또는 sharedprefs 제외를 권장한다. 이 티켓(문서) 범위 밖 — 별 티켓 후보.
- P-3 개정 이력 목록 미생성은 타당하다. 만들면 새 절 id 가 생겨 체크리스트 표·`#changes` 문장을 함께
  고치는 별건이 된다.
- P-4 `docs/RELEASE.md` "### 47." 표와 코드 주석은 Android 저장소를 "EncryptedSharedPreferences" 로
  부른다. `flutter_secure_storage` 11.x 는 Jetpack `EncryptedSharedPreferences` 에서 자체 AES-GCM +
  KeyStore 래핑으로 옮겼다(`MigrationBackup.java` 가 ESP → 신규 마이그레이션). 방침 본문은 "Android
  암호화 저장소" 로 일반화해 적어 영향 없음. 내부 문서·주석만 다음 기회에 고치면 된다.
- P-5 ko `#rights`·10절에 줄표(—)가 3개 늘었다. impeccable `em-dash-overuse` 는 뜨지 않았다(위 §1).

## 6. 종합

요구 5개 항목 전부 충족, 기능·로직 변경 없음, ko·en 구조 동일, 방침의 모든 새 문장이 소스와 일치한다.
"기기 식별자 제거" 를 "새 토큰으로 교체" 로 바로잡아 쓴 점, 웹 삭제와 앱 삭제의 토큰 처리 차이를 주어로
구분한 점은 과장·축소 금지 제약을 정확히 지킨 것이다. MINOR 2건은 ko 한 문장의 한정어와 테스트 하나의
단정 강도 문제로, 머지 뒤 손봐도 된다.

판정: PASS
