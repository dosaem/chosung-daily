# 08: 앱 설정 `/config`·헬스체크 고도화·Sentry 백엔드

**What to build:** 앱이 시작할 때 최소 앱 버전·점검 여부·지원 언어·스토어 링크를 한 번에 받는다. 운영자는 DB 설정 행으로 점검 모드와 최소 버전을 바꿀 수 있다(토글 UI 는 16). `/health` 가 DB 장애면 503, Redis 장애면 200 + degraded 를 돌려주고 업타임 모니터가 그걸 보도록 한다. 서버·워커 에러가 Sentry 로 간다.

**Blocked by:** 01

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.10, §A' config·health, §C.29, §C.30. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] `AppSetting`(키·값) 테이블 + 마이그레이션(머지 직전 `flask db heads` 1개), `GET /config` 가 `min_app_version {ios, android}`, `maintenance {enabled, message}`, `languages`, `store_urls {ios, android}` 를 돌려준다(인증 없음, 캐시 60초)
- [ ] `store_urls` 와 Smart App Banner 용 `APP_STORE_ID` 의 출처는 환경변수 `STORE_URL_IOS`, `STORE_URL_ANDROID`, `APP_STORE_ID`(스토어 등록 전엔 빈 값 허용 → 응답에 null). `.env.example` 에 추가. 18 의 웹 배지·메타 태그도 같은 설정값을 쓴다
- [ ] `GET /health` 가 `{status, db, redis, apple_secret_expires_at(null 허용, 11 에서 채움)}` 을 돌려주고 DB 실패 503 / Redis 실패 200+`degraded` (테스트: `test_redis_failure_fallback.py` 패턴)
- [ ] `sentry_sdk` Flask·Celery 통합이 `SENTRY_DSN` 있을 때만 활성, 릴리스·환경 태그 포함
- [ ] README "설계 판단" 에 "점검·최소 버전을 서버 설정으로", "헬스체크 등급" 추가, 운영 절에 UptimeRobot 등록(사람) 메모

## 리뷰 노트 (plan-review r1)

- P2-13: `store_urls`·`APP_STORE_ID` 출처를 환경변수로 확정, 18 이 같은 값을 씀
