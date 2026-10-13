# 08: 앱 설정 `/config`·헬스체크 고도화·Sentry 백엔드

**What to build:** 앱이 시작할 때 최소 앱 버전·점검 여부·지원 언어·스토어 링크를 한 번에 받는다. 운영자는 DB 설정 행으로 점검 모드와 최소 버전을 바꿀 수 있다(토글 UI 는 16). `/health` 가 DB 장애면 503, Redis 장애면 200 + degraded 를 돌려주고 업타임 모니터가 그걸 보도록 한다. 서버·워커 에러가 Sentry 로 간다.

**Blocked by:** 01

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.10, §A' config·health, §C.29, §C.30. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] `AppSetting`(키·값) 테이블 + 마이그레이션, `GET /config` 가 `min_app_version {ios, android}`, `maintenance {enabled, message}`, `languages`, `store_urls` 를 돌려준다(인증 없음, 캐시 60초)
- [ ] `GET /health` 가 `{status, db, redis, apple_secret_expires_at(null 허용, 11 에서 채움)}` 을 돌려주고 DB 실패 503 / Redis 실패 200+`degraded` (테스트: `test_redis_failure_fallback.py` 패턴)
- [ ] `sentry_sdk` Flask·Celery 통합이 `SENTRY_DSN` 있을 때만 활성, 릴리스·환경 태그 포함. `.env.example` 갱신
- [ ] README "설계 판단" 에 "점검·최소 버전을 서버 설정으로", "헬스체크 등급" 추가, 운영 절에 UptimeRobot 등록(사람) 메모
