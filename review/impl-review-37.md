# 티켓 37 최종 리뷰 — 릴리스 문서 완성 · 실기기 체크리스트 · 설계 판단 항목 점검

리뷰어: Phase4 Final Reviewer (task_b5d8509e05c5), 라운드 1, 2026-10-15.
대상: 브랜치 `dosaem/t37-release-docs-device-checklists`, `git diff main...HEAD`(13 파일, +1176/−15),
커밋 `5aee430`~`d85afe9` 9개. 로컬 `main` 기준(origin/main 은 쓰지 않았다).
이전 라운드 없음. 결함 ID 는 `D-37-1` 부터.

문서 티켓이라 "동작" 대신 **문서가 코드·워크플로·설정과 일치하는가**를 봤다. 증거 문서
(`review/impl-evidence-37.md`)의 주장은 믿지 않고 아래 §2 처럼 직접 돌리고 대조했다.
코디네이터 리뷰 메모(msg_6b5c34862f14)의 5개 항목은 §3 끝에 따로 답했다.

## 1. 티켓 체크박스별 충족 여부

| # | 체크박스 | 판정 | 근거(직접 확인) |
|---|---|---|---|
| ① | `docs/RELEASE.md` D0~D3(운영자 계정 두 개·제출일 기준 target SDK/Billing 8+·Grace Period·Data safety 삭제 URL·ASC 이름 중복), NAS 첫 배포(프로젝트명·볼륨), 복구 리허설, secrets 표 통합 | **충족** | `## 사람 작업 순서 (D0~D3)` 에 D0 4·D1 13·D2 7·D3 15 항목. 두 계정(`dosaem90@gmail.com`·`hsseo@dosaem.com`)은 이미 `main` 의 `CONTEXT.md:35`·RELEASE 371 행에 있던 값이라 새로 노출된 개인정보가 아니다. D2 에 Grace Period 16일·"Hidden Vowels: Daily Word", D3 에 `docker volume ls`·복구 리허설·`/account/delete`·"Billing 7 은 2026-08-31 로 제출이 막혔다". secrets·variables 표는 §2-④ 처럼 **양방향 전수 대조**해 워크플로 6개가 쓰는 21 secrets + 9 vars 와 정확히 일치하고 "쓰는 워크플로" 칸도 30행 전부 실제 파일과 같다 |
| ② | 실기기 체크리스트 통합(각 항목 기대 결과) | **충족** | 5 소절 42 항목, 전부 `조작 → 기대 결과` 꼴. 스펙 Testing 의 6 키워드 + 티켓 추가 14 키워드 전부 있음. 기대 결과의 문구·상수를 코드와 대조했다(§2-⑤): 앱 문구 7개는 `mobile/assets/translations/ko.json`·`mobile/lib` 에 실재, `maxPending = 1 + 7`, `reminderHour = 20`, `inexactAllowWhileIdle`, 배너 50/90·728 경계(`banner_size.dart`), compact < 600·Split View 320dp(`app_breakpoint.dart`), 다이얼로그 최대 폭 560(`adaptive_sheet.dart`), `maskEmail` 이 `privaterelay` 주소도 마스킹(테스트 `account_controller_test.dart:826`), 4040010 폴백(`app/clients/app_store.py:50`), `chosung_token`·`chosung_history_`(`web/static/app.js:2,5`), `apple_revocation_retry` 테이블 |
| ③ | 16 의 법적 항목을 D1·D3 에 통합 | **충족** | RELEASE `### 16.` 의 체크박스 8개(통신판매업·축약 주소 적법성·보호책임자·전문가 검토·ASC EULA·Data safety 일치·구독 고지 일치·렌더 확인)와 대조 — D1 에 통신판매업(면제)·보호책임자·주소/전화·전문가 검토(안 받음, 축약 주소 해석은 여기에 흡수), D3 에 Data safety 일치·구독 고지 일치·EULA 미입력 확인. 사용자 확정 내용이 `user-todo.md` #1~#5 와 같다 |
| ④ | README "설계 판단" §C.32 열 항목 점검, 빠진 것 보강 | **충족** | `### 37. 설계 판단 항목 점검` 표의 열 항목이 가리키는 README 절 15개를 전부 열어 봤다 — 모두 실제 `### ` 제목이고 17~103줄의 본문에 근거가 있다. 없던 것은 KST 하나뿐이고 새 `### 37. KST 고정` 절의 사실 주장을 코드와 대조했다: `app/config.py:8` `KST = ZoneInfo("Asia/Seoul")`, `celery_app.py:15` `timezone = "Asia/Seoul"`, Beat 00:00 배정·00:05 통계·04:10 접속기록 삭제(`app/tasks/scheduled.py:75,79,95`), backup `BACKUP_AT: "04:00"`(`docker-compose.prod.yml:121`), `NotificationPlan.kstOffset = 9h`, `web/static/app.js:14` 고정 오프셋 — 전부 일치. 대안(로컬 자정)·비용·되돌리기 난이도가 한 단락씩 있다 |
| ⑤ | README Flutter 절 최종 + 면접 설명 범위 문장 | **충족** | `### 22.` 끝에 "**면접 설명 범위.**" 문단과 세 축 → 절 색인 표. 표가 가리키는 "24."·"30."·"31."·"32."·"33." 은 실제 README 제목(1393·1967·2576·2657·2755행) |
| ⑥ | 스펙 미정 항목 갱신(9·12·13·14·18·19·20·21·22·23·24 확정 + 남은 것 "운영 데이터 후") | **충족**(해석 있음, 참고 1) | 1~27 상태 표를 원문 항목과 한 줄씩 대조 — 확정 티켓 번호·결론이 원문의 "(티켓 NN 반영)" 블록과 같다. 열린 4개(1·6·10·11)만 "운영 데이터 후". 10 의 "조건은 이미 충족" 은 `web/static/app.js`·`mobile/lib` 에 `chosung` 필드를 읽는 곳이 없고 서버는 아직 보낸다(`puzzle_cache.py:75`)는 것으로 확인 |
| ⑦ | `docs/agents/`·`CONTEXT.md`·`docs/adr/` 대조 | **충족** | `docs/agents/` 4파일의 주장(루트 `CONTEXT.md`, `docs/adr/`, `CLAUDE.md` 아직 없음) 사실. 추가 용어 4개는 각각 `paywall_sheet.dart`·`google_ad_service.dart`·`entitlement_schedule.dart`·`onboarding_screen.dart` 가 짝이고 설명이 코드와 맞는다 — 온보딩 "완료 표시는 기기에 남아 계정을 지워도 다시 뜨지 않는다" 는 `onboarding_store.dart`(`SharedPreferences` 키 `onboarding_seen`)와 `mobile/lib/account/` 가 그 키를 건드리지 않는 것으로 확인. ADR 0003 보강 문장은 스펙 "(티켓 33 반영)" 블록·README "33." 과 같은 내용 |
| ⑧ | 옛 티켓 번호 주석 정리 | **충족** | 증거의 11곳 외에 **독립 전수 조사**를 했다(§2-⑥): 코드·문서 전체에서 `티켓 (16|23~34)` 참조를 뽑아 `git blame HEAD` 로 그 줄을 만든 커밋의 티켓을 보고, 재배정 전 티켓(01~13·15·17·19~22)이 쓴 줄이 남아 있는지 봤다 — **0건**. `home_shell.dart` 에는 `티켓` 문자열이 없다(티켓 본문의 예시는 이미 사라진 상태) |

## 2. 직접 실행한 검증

전용 자원(`TEST_DATABASE_URL=…/chosung_daily_test_t37`, `TEST_REDIS_URL=redis://localhost:6379/11`,
`TEST_MIGRATION_DATABASE_URL=…/chosung_daily_test_t37_migrations`)을 그대로 재사용했다. DB 를
새로 만들지 않았고 공용 `chosung_daily_test` 는 쓰지 않았다.

| 항목 | 명령 | 결과 |
|---|---|---|
| ① ruff | `uv run ruff check .` | `All checks passed!` |
| ② 마이그레이션 head | `FLASK_APP=wsgi.py uv run flask db heads` | `b1c7d4e0a932 (head)` 1줄 (`migrations/` 무변경) |
| ③ 전체 pytest | `uv run pytest -q -p no:cacheprovider` (전용 DB) | `1633 passed in 828.77s (0:13:48)`, exit 0 — 실패·에러 0, 1회 실행으로 끝(재실행 불필요) |
| ④ secrets·variables 표 전수 대조 | `.github/workflows/*.yml` 의 `secrets.*`·`vars.*` 집합 ↔ 통합 목차 첫 칸 집합을 `comm` 으로 양방향 비교 + 행마다 "쓰는 워크플로" 칸 ↔ 실제 파일 | 누락 0 · 잉여 0 · 워크플로 칸 30/30 일치 |
| ⑤ 통합 절 식별자 전수 대조 | `## 사람 작업 순서` ~ `## 알려진 한계` 의 백틱 식별자 102개(환경변수·파일·경로·클래스·테이블·워크플로명)를 RELEASE.md 밖 레포 전체에서 `grep -F` | 미존재 0 |
| ⑥ 옛 번호 전수 조사 | `grep -rnE "티켓 (16\|2[3-9]\|3[0-4])"` (app·mobile·web·tests·docs·README·CONTEXT·.github) → 각 줄 `git blame HEAD` → 커밋 제목의 티켓 번호 | 재배정 전 티켓이 쓴 줄 0건 |
| ⑦ flutter analyze | `cd mobile && flutter analyze` | `No issues found!` (Dart 변경은 주석 3줄뿐이라 `flutter test` 는 돌리지 않았다) |
| ⑧ 시크릿·PII 패턴 | 새 절에서 `BEGIN `, 전화번호·사업자번호 형식, `ca-app-pub`, `AIza`, `hooks.slack.com/services/`, 번길·동·호 등 상세 주소 패턴 | 0건 |
| ⑨ 알려진 한계 ID | D-31-8·D-33-3·D-39-1·D-38-1·D-38-2·D-17-6 을 각 리뷰 파일에서 확인 | 전부 실재하고 MINOR, 해당 리뷰 최종 판정은 PASS |
| ⑩ `user-todo.md` 번호 | D0~D3 의 `#N` 18개 ↔ 그 파일 표의 1~18 행 | 항목 내용 일치(예 #6 단어 CSV, #13 ASC·구독·Grace, #17 백업 키). 이 브랜치는 그 파일을 수정하지 않았다 |

## 3. 결함 목록

BLOCKER 0 · MAJOR 0 · MINOR 0.

리뷰 범위에서 본 것 — 티켓 요구 누락 없음, 스펙과 다른 동작 없음(코드 동작 변경 자체가
없다: `app/services/word_service.py` 2줄·Dart 3파일 각 1줄은 전부 주석), 테스트는 실제
파일을 읽어 집합·제목·키워드를 대조하므로 항상 통과하는 대역이 아니다(증거 §1 의 red 를
믿지 않고 `git stash` 없이 확인했다: `main` 의 RELEASE·README 에는 통합 절·`### 37.`·면접
범위 문단이 없으므로 그 fixture 가 `assert heading in text` 에서 깨진다), 보안(값·주소
노출) 없음, 데이터 손상 가능성 없음, 병렬 티켓 공유 파일 규칙 — README 는 `### 37.` 두
절을 "설계 판단" 끝에, 스펙은 `## 미정 항목` 끝에, RELEASE 의 통합 절은 `## 티켓별 기록`
앞에 두었고 다른 티켓의 `### NN.` 본문은 옛 번호 3줄 외에 건드리지 않았다.

### 코디네이터 메모(msg_6b5c34862f14) 답

1. **전수 대조** — §2-④·⑤·⑥ 이 표본이 아니라 전수다. D0~D3 항목이 가리키는 `.env` 키 13개
   (`SENTRY_DSN`·`ADMIN_EMAILS`·`LEGAL_*` 3·`SUBSCRIPTION_PRODUCT_ID`·`STORE_URL_*`·`APP_STORE_ID`·
   `LOG_DIR`·`BACKUP_ENCRYPTION_CERT_FILE`·`ACCESS_LOG_RETENTION_DAYS`·`GOOGLE_BOOKS_API_KEY`)는
   `.env.example` 에 전부 있다.
2. **값·주소** — §2-⑧ 0건. 이메일 두 개는 `main` 에 이미 있던 운영자 계정이고, 주소는 "시·구까지만"
   이라는 **규칙**만 적혀 있고 값은 없다.
3. **법적 문구 ↔ 실제 처리** — 백업: D1·D3·알려진 한계 모두 "공개키 인증서만 NAS, 개인키 NAS 밖"
   으로 `openssl cms` 구현과 맞고 새 절에 `age` 언급 없음(`user-todo.md` #17 의 `age` 표기는 그
   파일 소유 세션의 몫이라 증거 §8 대로 손대지 않은 것이 맞다). 접속기록: "365일 보관·월 1회 점검" ↔
   `app/config.py:145` 기본 365. 광고 위치: D3 의 "위치 > 대략적인 위치 수집·공유 예" ↔
   `docs/play-data-safety.md:38` 같은 행. 방침 템플릿(`privacy.ko.html:234,279`)의 "압축·암호화한
   덤프, 복호화 키는 서버에 없음" 과도 일치.
4. **코드 변경 범위** — `app/services/word_service.py` 는 docstring 안의 "(티켓 16)" → "(티켓 23)"
   2곳뿐이고, Dart 3파일도 주석 1줄씩. 동작 변경 0.
5. 티켓 40 자리는 결함으로 세지 않았다.

## 참고 (결함 아님)

1. **미정 항목 상태 어휘.** 티켓은 "남은 것은 '운영 데이터 후'" 라 했지만 구현은 2·5 를 "범위 밖",
   4·7 을 "사람 D2/D3", 26 을 "알려진 한계" 로 적었다. Playwright E2E(5)·UMP 문구(7)를 "운영 데이터
   후" 로 적으면 거짓이 되므로 사실대로 쓴 쪽이 맞고, 증거 §8 에 이유가 적혀 있다. 다음 사람이
   티켓 문구와 다르다고 놀라지 않게 여기 적어 둔다.
2. **README 에 `### 37.` 절이 둘**(점검표·KST). 같은 번호 절이 여럿인 것은 01·02·03·04·07·15·17·23
   도 마찬가지라 레포 관례다. 다른 문서가 "README 37." 로 가리킬 때는 스펙 표처럼 제목 전문을 쓰는
   편이 안전하다.
3. **`tests/test_app_deploy_workflow.py`(티켓 34 소유) 1곳 수정.** 통합 목차가 `"### 34."` 를 가리키는
   순간 그 헬퍼가 엉뚱한 토막을 읽게 된 것이라 앵커를 줄 머리로 옮긴 것이고 단언은 그대로다. 같은
   파일의 114개가 전체 스위트 안에서 통과했다.
4. **새 테스트의 `_section`/`_subsection` 도 "문자열 첫 등장" 에서 자른다.** 지금은 각 제목 문자열이
   본문 인용보다 먼저 나오지 않아 맞게 동작하고, RELEASE 쪽은
   `test_every_ticket_section_heading_appears_once_at_the_start_of_a_line` 이 지킨다. README 쪽
   (`### 37. 설계 판단 항목 점검`, `### 22. Flutter 앱`)은 같은 보호가 없으니 나중에 누가 그 제목을
   본문에서 따옴표로 인용하면 §9 와 같은 그림자가 생길 수 있다 — 그때 `"\n### "` 앵커로 바꾸면 된다.
5. `test_secret_index_does_not_carry_values` 는 `BEGIN `·`ca-app-pub-` 두 패턴만 본다. 값 유출을 막는
   주 방어선은 리뷰(§2-⑧)이지 이 테스트가 아니다.
6. 실기기 42항목은 아무도 실행하지 않았다(증거 §8 과 같은 말). 이 티켓의 산출물은 목록이고, 수행은
   D3 사람 차례다.

판정: PASS
