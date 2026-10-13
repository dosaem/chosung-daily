# 05: 자정 배정 언어별 실행·캐시·잔량 Slack 알림

**What to build:** KST 자정에 언어별로 오늘의 퍼즐이 각각 배정·커밋되고, 한 언어(예: en 단어 고갈)가 실패해도 다른 언어는 정상 배정되며 운영자가 Slack 으로 실패를 받는다. 언어별 단어 풀 잔량이 14일치 미만이면 매일 Slack 으로 알림이 온다.

**Blocked by:** 03

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.1 자정 배정, §A.12, Testing Celery. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] 자정 배정 서비스 함수가 언어 하나를 인자로 받아 배정·캐시 워밍·커밋까지 끝내고, Celery 태스크가 지원 언어를 순회하며 각각 호출한다. 한 언어 실패 → `notify_operator` 호출 후 다음 언어 진행(테스트: en 단어 0개일 때 ko 는 배정되고 Slack 래퍼가 en 실패로 1회 호출)
- [ ] 잔량 계산 서비스 함수(언어별 미사용 단어 수 → 며칠치)가 있고 Beat 가 매일 1회 14일 미만 언어를 Slack 으로 알린다(테스트: 서비스 함수 직접 호출 + 태스크 배선 확인)
- [ ] 배정 시 `puzzle:{date}:{lang}` 캐시를 쓰고 Redis 장애 시 `safe_redis_call` 로 DB 폴백(기존 패턴 유지)
- [ ] Beat 스케줄(KST)에 언어별 배정·잔량 알림이 등록되고 README 운영 절에 기록된다
- [ ] README "설계 판단" 에 "언어별 각각 커밋·부분 실패 허용" 추가
