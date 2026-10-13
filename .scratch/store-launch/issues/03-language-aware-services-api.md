# 03: 서비스·API 언어 인지화 — 게스트 언어 선호·퍼즐 조회·캐시 키·언어 무관 연속 기록

**What to build:** 게스트가 퍼즐 언어를 고르면(생성 시 또는 `PATCH /me`) 그 언어의 오늘 퍼즐을 받는다. `GET /puzzles/today` 응답에 `puzzle_id`, `language`, `mask` 가 들어가고 `chosung` 은 ko 호환용으로 남는다. 통계·리더보드는 언어별로 분리되고 `?language=` 로 명시할 수 있다. 연속 기록은 언어와 무관하게 "그 날 하나라도 맞추면" 이어지고, 같은 날 ko·en 둘 다 맞추면 `solved_count` 가 2 오른다. rate limit 은 언어와 무관하다.

**Blocked by:** 02

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.1(서비스·API), §A.3, §A.4, §A', Testing 필수 케이스. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] `POST /guests {puzzle_language?}` 로 초기 언어를 정하고(기본 ko, 미지원 값 `VALIDATION_ERROR`), `PATCH /me {puzzle_language}` 로 바꾸며, `GET /me/stats` 에 `puzzle_language` 가 포함된다
- [ ] `GET /puzzles/today` 가 게스트 선호 언어의 퍼즐을 돌려주고 응답에 `puzzle_id`, `language`, `mask`, `length` 가 있다. `chosung` 필드는 ko 에서 현행 값, en 에서는 `mask` 의 `r` 글자 기반 문자열(또는 null) — 응답 스키마에 명시
- [ ] Redis 키가 `puzzle:{date}:{lang}`, `stats:{date}:{lang}`, `lb:{date}:{lang}` 로 분리되고 rate limit 키에는 언어가 없다(테스트: 언어를 바꿔도 같은 게스트의 rate limit 카운터가 이어짐)
- [ ] `GET /puzzles/today/stats?language=`, `GET /puzzles/today/leaderboard?language=` 가 명시 언어(기본 게스트 선호)로 동작하고 응답에 `language` 가 있다
- [ ] 연속 기록 서비스 함수: `last_solved_date == today` 면 no-op, `== yesterday` 면 +1, 그 외 1. 테스트: 같은 날 ko→en 정답 시 streak 유지·`solved_count` +2
- [ ] 같은 날 ko/en 두 퍼즐이 공존하고 언어 변경 후 조회·캐시가 분리되는 테스트 통과. 기존 테스트 통과(픽스처 `today_puzzle(language)` 추가)
- [ ] README "설계 판단" 에 "연속 기록 언어 무관", "캐시 키 언어 분리·rate limit 언어 무관" 추가. README API 표 갱신
