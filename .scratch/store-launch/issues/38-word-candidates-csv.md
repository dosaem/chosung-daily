# 38: 단어 후보 CSV 생성 — ko/en general 각 150개 이상 + 검증 스크립트

**What to build:** 운영자가 `/admin/words/import` 에 그대로 올릴 수 있는 단어 후보 CSV(ko/en `general` 각 150개 이상)와, 올리기 전에 로컬에서 형식·규칙 위반을 0건으로 확인하는 검증 스크립트. 사람은 후보를 훑어 보고 마음에 안 드는 행만 지운 뒤 올린다. 정답은 레포에 평문으로 남지 않는다.

**Blocked by:** 15, 23

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §D0(단어 CSV ko/en 각 ≥120, 심사 전 en 30일 배정 확인), §A.11(CSV 포맷), README "운영: 단어 CSV 업로드" 의 LLM 프롬프트 골자. 용어는 `CONTEXT.md`.

**배경(2026-10-15 사용자 결정):** 단어 CSV 는 아직 없고 사람이 직접 만들지 않는다 — "후보 생성을 워커에게 시키자". 생성 규칙은 README 의 프롬프트 골자를 그대로 따른다(ko: 2~5글자 명사·일상어·고유명사/유행어 제외·공백/기호 없음, 힌트 한 줄·정답 글자 미포함; en: 자음 뼈대로 알아볼 수 있는 2~12자·하이픈/공백은 두 단어까지).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다.

**산출물 위치:** 정답이 공개 레포에 평문으로 남으면 퍼즐이 미리 새므로 CSV 는 커밋하지 않는다 — `data/word-candidates/`(gitignore 에 추가) 에 `ko-general-01.csv`·`en-general-01.csv` 로 두고, 브랜치에는 검증 스크립트·테스트·문서만 들어간다. CSV 파일 자체는 `review/impl-evidence-38.md` 에 **경로와 행 수·검증 결과만** 적고, 파일은 코디네이터가 사용자에게 전달한다(NAS 접속·업로드는 사람).

- [ ] `data/word-candidates/ko-general-01.csv` — `language,category,answer,hint` 헤더, `ko,general` 150행 이상. 정답 2~5글자 완성형 한글만(공백·숫자·기호·영문 없음), 인명·지명·브랜드·유행어 없음, 같은 파일 안 중복 없음, `data/seed_words.csv` 와도 겹치지 않음. 힌트는 1~60자 한 줄, **정답에 쓰인 음절을 하나도 포함하지 않고** 뜻·용도·분류로만 설명, 따옴표·쉼표 없음
- [ ] `data/word-candidates/en-general-01.csv` — `en,general` 150행 이상. 정답은 소문자 a–z 와 공백/하이픈만, 2~12자, 공백·하이픈은 최대 1개(두 단어까지), 고유명사 없음, 모음을 가려도 자음 뼈대로 추측 가능한 흔한 단어(예 `mountain`, `keyboard`; `aeon`·`eye` 처럼 모음이 대부분인 단어 제외 — 모음 비율 50% 이하). 힌트는 정답 단어(와 그 복수형)를 포함하지 않는 한 줄
- [ ] 두 파일 모두 난이도 섞기: 쉬움·보통·어려움이 대략 4:4:2 가 되도록 하고, `review/impl-evidence-38.md` 에 각 파일 20행 표본과 난이도 분포 근거를 적는다
- [ ] 검증 스크립트 `scripts/check_word_csv.py <csv>...` — `app.services.word_service.parse_word_input` 으로 행마다 검증(DB 없이), 추가로 위 언어별 규칙(글자 범위·길이·힌트에 정답 포함·파일 내 중복·`data/seed_words.csv` 와 중복)을 검사해 위반 행을 `줄번호: 사유` 로 출력하고 위반이 있으면 종료 코드 1. 두 후보 파일에 대해 실행 결과 **0건**을 증거 문서에 붙인다
- [ ] 스크립트 테스트 `tests/test_check_word_csv.py` — 임시 CSV 로 정상/힌트에 정답 포함/길이 초과/중복/잘못된 category 각 1건이 올바른 사유로 잡히는지, 정상 파일은 종료 코드 0 인지(실제 후보 파일은 테스트가 읽지 않는다 — 커밋되지 않으므로)
- [ ] `import_word_rows` 드라이런: 테스트 DB(기존 픽스처)에서 후보 파일을 `import_word_rows` 로 적재해 추가 ≥150·오류 0 임을 로컬에서 확인하고 결과 수치를 증거 문서에 적는다(테스트 코드로 고정하지 않는다 — 파일이 레포에 없음)
- [ ] `book_title` 후보: `flask search-books` 가 API 키 없이 동작하면 ko·en 각 20권을 `--add` 없이 검색해 `data/word-candidates/{ko,en}-book-01.csv` 로 만든다(실존 확인된 제목만, 힌트는 저자·분류). 키가 필요해 안 되면 증거 문서에 "사람이 `flask search-books` 로 넣는다" 로 남기고 이 항목은 건너뛴다
- [ ] `.gitignore` 에 `data/word-candidates/` 추가, README "운영: 단어 CSV 업로드" 절 끝에 `scripts/check_word_csv.py` 사용법 한 단락(올리기 전 로컬 검증), `docs/RELEASE.md` 에 `### 38.` — 사람이 할 일: 후보 파일 훑어보기 → 마음에 안 드는 행 삭제 → `/admin/words/import` 업로드 → `/admin/schedule` 에서 ko·en 각 30일 이상 배정 확인(심사 전 en 30일)
- [ ] 테스트 전체 통과, `ruff` 0건

**하지 않는 것:** 운영 서버 업로드(사람), 단어 DB 직접 적재, 잔량 알림 로직 변경(05), 책 API 키 발급.
