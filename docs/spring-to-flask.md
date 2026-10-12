# Spring → Flask 개념 대응표

Java/Spring, TypeScript/NestJS로 6년차 백엔드를 하다가 Flask를 처음 써보면서
정리한 대응표다. 면접에서 "Spring이었다면 어떻게 했을까"를 설명할 수 있어야
해서, Phase마다 설계 판단을 내릴 때 실제로 이렇게 비교하며 진행했다
(각 Phase의 자세한 판단 근거는 [`README.md`](README.md)의 "설계 판단" 참고).

## 한눈에 보기

| Spring/Java | 이 프로젝트 (Flask) | 비고 |
|---|---|---|
| `@SpringBootApplication`, `ApplicationContext` | `create_app()` 팩토리 (`app/__init__.py`) | Spring은 컴포넌트 스캔으로 빈을 자동 수집, 여긴 `register_*(app)` 호출을 직접 나열 |
| `application.yml` + `spring.profiles.active` | `app/config.py`의 `Config` 클래스 계층 + `CONFIG_BY_NAME` | profile 전환 = `create_app(config_name)`에 문자열 넘기기 |
| `@RestController`, `@RequestMapping` | Flask `Blueprint` (`app/api/*.py`) | |
| `@Service` | `app/services/*.py`의 함수들 | Spring은 클래스+DI, 여긴 상태 없는 모듈 함수 — DI 컨테이너가 없어서 의존성은 그냥 import |
| `@Repository`, `JpaRepository` | `app/repositories/*.py` | Spring Data JPA의 메서드 이름 기반 자동 쿼리 생성이 없어서, 쿼리를 SQLAlchemy로 직접 작성 |
| `@Entity` | `app/models/*.py`의 `db.Model` 서브클래스 (SQLAlchemy) | |
| DTO / Java `record` | `app/schemas/*.py`의 pydantic `BaseModel` | 요청 검증 + 응답 직렬화를 겸함 |
| Bean Validation (`@Valid`, `@NotNull`) | pydantic 필드 타입/제약 | |
| `@ControllerAdvice` + `@ExceptionHandler` | `app/errors.py`의 `AppError` 계층 + `register_error_handlers` | |
| `@Transactional` | "서비스 함수 하나 = 커밋 하나" 수동 규칙 | Spring은 선언적(어노테이션), Flask-SQLAlchemy는 `db.session.commit()`을 직접 호출해야 함 — 까먹으면 그냥 반영이 안 됨 |
| `@Lock(LockModeType.PESSIMISTIC_WRITE)` | `SELECT ... FOR UPDATE` (`guest_stats_repository.lock_for_guest`) | |
| Flyway / Liquibase | Flask-Migrate (Alembic) | `flask db migrate`가 모델 변경을 감지해서 마이그레이션 스크립트를 생성 — Flyway처럼 직접 SQL을 안 써도 됨(단, 생성된 스크립트 검토는 필수) |
| `@Scheduled`, Spring Batch | Celery Beat (`celery_app.py`의 `beat_schedule`) | |
| `@Async`, `@EnableAsync` | Celery 태스크 (`app/tasks/scheduled.py`) | Spring 비동기는 같은 프로세스의 스레드풀, Celery는 완전히 별도 워커 프로세스(+ 브로커) |
| Spring Cache (`@Cacheable`) | 수동 Cache-Aside (`app/services/puzzle_cache.py`) | 선언적 어노테이션이 없어서 캐시 get/miss/set을 직접 작성 |
| Spring Security `OAuth2LoginConfigurer` | Authlib (`app/api/oauth.py`) | `state`(CSRF) 자동 생성·검증은 Authlib도 똑같이 해줌. 다만 "로그인 세션 == 어느 계정"을 연결하는 로직은 프레임워크가 안 챙겨줘서 직접 만들다가 CSRF 버그를 하나 만들었다(README 참고) — Spring Security를 썼어도 이 비즈니스 로직 자체는 직접 짜야 했을 것 |
| `HttpSession` | Flask `session` (서명된 쿠키) | |
| Spring Cloud Gateway RateLimiter / Bucket4j | 직접 구현한 고정 윈도우 rate limit (`app/api/rate_limit.py`) | |
| Resilience4j `@CircuitBreaker`/`@Fallback` | `safe_redis_call` (`app/utils/redis_safe.py`) | Redis 장애 시 조용히 기본값으로 폴백 — 서킷브레이커의 "open 상태에서 즉시 폴백"과 비슷한 효과를 훨씬 단순하게(상태 추적 없이) 구현 |
| JUnit5 + Mockito | pytest, Mock 최소화 | 실제 MySQL/Redis를 붙여서 테스트 — Spring이면 `@DataJpaTest` + Testcontainers에 가까운 방식 |
| Testcontainers | docker-compose의 실제 MySQL/Redis 컨테이너 | |
| Gradle / Maven | uv (`pyproject.toml`) | |
| Spring Boot DevTools (핫 리로드) | Flask 디버그 모드(`DEBUG=True`) | |
| `WebClient` / `RestTemplate` | `requests` (`app/services/book_lookup_service.py`) | 카카오/알라딘 책 검색 API 호출 |

## 제일 크게 느낀 차이

**DI 컨테이너가 없다.** Spring은 `@Autowired`로 뭐가 어디서 오는지 몰라도 동작하는데,
Flask/이 프로젝트 구조에서는 의존성이 전부 명시적인 `import`다. 처음엔 번거로워
보였는데, 오히려 "이 함수가 뭘 쓰는지"가 import문만 봐도 다 보여서 추적이 쉬웠다.
대신 전역 상태(싱글턴) 관리는 직접 챙겨야 한다 — `db`/`migrate`/`redis_client`/
`oauth` 같은 확장 객체를 어떻게 보관하느냐에 따라 테스트나 멀티 프로세스
환경에서 조용히 깨질 수 있다는 걸 이 프로젝트에서 두 번(redis, OAuth) 직접
겪었다. Spring이었다면 빈 스코프(싱글턴/프로토타입)를 프레임워크가 관리해줘서
이런 종류의 버그 자체가 날 일이 적었을 것 — 그 대신 "왜 안 되는지" 디버깅하기는
더 어려웠을 수도 있다.

**트랜잭션이 선언적이지 않다.** `@Transactional` 한 줄이면 끝나는 걸, 여기선
"서비스 함수 끝에서 commit 한 번"이라는 **규칙**을 사람이 지켜야 한다. 코드
리뷰 없이 막 짜면 트랜잭션 경계가 뒤죽박죽될 수 있다는 뜻이라, 이 프로젝트
전체에서 일관되게 지키는 걸 의식적으로 신경 썼다(README의 "트랜잭션 경계" 절).

**비동기/스케줄링이 별도 프로세스다.** Spring `@Async`/`@Scheduled`는 같은 JVM
안의 스레드풀에서 도는데, Celery는 완전히 다른 프로세스(워커)가 브로커(Redis)를
거쳐 통신한다. 그래서 Celery 태스크가 Flask 앱 컨텍스트(DB 세션, 설정)에
접근하려면 자기 몫의 앱 인스턴스를 따로 만들어야 했고, 이게 테스트 환경과
충돌하는 문제로 이어졌다(`celery_app.py`가 만드는 앱과 pytest가 만드는 앱이
달라서, 태스크 안의 로직을 서비스 함수로 뽑아내야 했다 — README의 "Celery Beat"
절 참고).
