# 05: 자정 배정 언어별 실행·캐시·잔량 Slack 알림

**What to build:** KST 자정에 언어별로 오늘의 퍼즐이 각각 배정·커밋되고, 한 언어(예: en 단어 고갈)가 실패해도 다른 언어는 정상 배정되며 운영자가 Slack 으로 실패를 받는다. 언어별 단어 풀 잔량이 14일치 미만이면 매일 Slack 으로 알림이 온다. 현행 배정 함수·CLI·일일 통계 flush 가 모두 언어를 인지한다.

**Blocked by:** 03

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.1 자정 배정, §A.12, Testing Celery. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] 현행 `schedule_puzzles` 가 `(language, days)` 를 받아 그 언어의 미사용 단어만 고르고(02 머지 후 ko 퍼즐에 en 단어가 섞이지 않음), CLI `schedule-puzzles` 에 `--language` 옵션, `flush_daily_stats_for_yesterday` 는 언어별 키를 순회한다(테스트 각각)
- [ ] 자정 배정 서비스 함수가 언어 하나를 인자로 받아 배정·캐시 워밍·커밋까지 끝내고, Celery 태스크가 지원 언어를 순회하며 각각 호출한다. 한 언어 실패 → `notify_operator` 호출 후 다음 언어 진행(테스트: en 단어 0개일 때 ko 는 배정되고 Slack 래퍼가 en 실패로 1회 호출)
- [ ] 잔량 계산 서비스 함수(언어별 미사용 단어 수 → 며칠치)가 있고 Beat 가 매일 1회 14일 미만 언어를 Slack 으로 알린다(테스트: 서비스 함수 직접 호출 + 태스크 배선 확인)
- [ ] 배정 시 `puzzle:{date}:{lang}` 캐시를 쓰고 Redis 장애 시 `safe_redis_call` 로 DB 폴백(기존 패턴 유지)
- [ ] Beat 스케줄(KST)에 언어별 배정·잔량 알림이 등록되고 README 운영 절에 기록된다. 선택: `celery_app.py` 의 `beat_schedule` 딕셔너리를 모듈별 리스트를 합치는 구조로 바꿔 11·13·14 의 추가가 충돌하지 않게 한다
- [ ] README "설계 판단" 에 "언어별 각각 커밋·부분 실패 허용" 추가

## 리뷰 노트 (plan-review r1)

- P1-10: 현행 `schedule_puzzles`·CLI·`flush_daily_stats_for_yesterday` 언어 인지화를 완료 조건으로 명시(16 의 30일 배정표가 이 함수를 씀)
- P2-20: Beat 스케줄 모듈별 등록 구조는 선택 사항으로 넣음
