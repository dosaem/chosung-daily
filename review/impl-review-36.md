# 티켓 36 최종 리뷰 — 라운드 1

- 기준: 로컬 `main` = `055b56ce43df639e63a39d096c1e3b43b275ec1d`, 구현 HEAD = `0ab7df9506f78db24aee76488a3381afe5c1e569`.
- 티켓, 스펙 §A.15·C.28·C.33·미정 27, `git log main..HEAD`, `git diff main...HEAD`, `review/impl-evidence-36.md`를 대조했다. 증거 문서의 통과 주장을 그대로 채택하지 않았다.
- 코디네이터가 승인한 CMS 공개키 방식과 환경변수 이름 변경은 결함이 아니다. 하위 에이전트·프로덕션·외부 서비스 호출 없이 검증했다.

## 체크박스별 판정

| 티켓 체크박스 | 판정 | 근거 |
|---|---|---|
| 백업 암호화 | 미충족 | 스크립트의 스트리밍 암호화·실패 정리·알림·새 확장자 보존은 구현됐지만, 실제 backup 서비스에 인증서 설정이 전달되지 않아 백업이 생성되지 않는다(D-36-1). |
| 복구 | 충족 | `restore.sh`가 키 유무 및 복호화+gzip 전체 검사를 MySQL 호출 전에 수행한다. 올바른 키·잘못된 키·손상·기존 평문 덤프 경로를 실행 테스트로 확인한다. |
| 키 절차 문서 | 증거 부족 | RELEASE §36에 생성·NAS 밖 두 곳 보관·분실 경고·교체·평문 경로 제거 절차가 있다. 다만 요구한 암호화 복구 리허설 실측 기록은 해당 절에 없고 미완료 체크박스다. 증거 문서의 수동 파이프 복구는 `restore.sh` 전체 실행과 다르므로 실제 배포 리허설 완료로 인정하지 않는다. |
| 감사 로그 테이블·기록 지점 | 미충족 | migration·INSERT 리포지토리·행위 표·응답 훅·403 기록은 존재한다. 동시 요청에서 기록 일부가 유실된다(D-36-3). |
| 위변조 검출 | 충족 | 행 내용·중간 행 삭제를 해시 체인으로 검출하는 코드와 실제 DB 테스트가 있다. `updated_at` 및 리포지토리 update/delete API가 없다. 보존 삭제 후 첫 행 연결은 검사하지 않는 한계가 명시돼 있다. |
| 접근 로그 | 미충족 | 포맷은 IP·시각·메서드·쿼리 없는 경로·상태·크기·UA·시간을 포함하고 인증 헤더·쿠키·쿼리를 제외한다. 그러나 Gunicorn 쓰기 경로가 공유 볼륨 경로와 다르다(D-36-2). |
| 보관·삭제 | 미충족 | DB 일일 만료 삭제, 파일 회전·gzip·기간별 삭제, 실패 알림은 개별 구현됐다. 실제 app 로그가 backup의 회전 경로로 들어오지 않는다(D-36-2). |
| 점검 | 충족 | 월별 행위별 건수·거부 수·체인 검증 CLI와 RELEASE 월 1회 실행·보관 체크박스가 있다. |
| 법적 문서 동기화 | 미충족 | ko/en·체크리스트·RELEASE §16·미정 27의 문구 갱신과 D-16-5 연결 해제 안내 수정은 확인했다. 하지만 “매일 백업”, “접속기록 1년 보관·자동 삭제”라는 고지는 D-36-1~3 때문에 실제 운영 경로와 아직 일치하지 않는다. `LEGAL_EFFECTIVE_DATE`는 같은 날인 2026-10-14라 유지한 사유가 타당하다. |
| env·README 설계 판단·기존 테스트·ruff | 미충족 | 승인된 env 이름과 §36 설명, 365일 및 근거 조문 인용은 있다. 설정을 선언한 것만으로 컨테이너 전달이 보장되지 않는다(D-36-1~2). 테스트·ruff 결과는 아래 별도 기록. |

## 직접 검증

- 전용 자원: `TEST_DATABASE_URL`은 localhost의 기존 `chosung_daily_test_t36`, `TEST_MIGRATION_DATABASE_URL`은 기존 `chosung_daily_test_t36_migrations`, `TEST_REDIS_URL`은 localhost Redis DB 10으로 지정했다. 접속 성공했으며 기본 테스트 DB로 폴백하지 않았다. 새 DB는 만들지 않았다. 접속 자격정보는 이 문서에 적지 않는다.
- `uv run pytest -q` → **1345 passed in 774.52s (0:12:54)**, 종료 코드 0. 전체 실행을 끝까지 완료했다.
- `uv run pytest tests/test_backup_restore.py tests/test_access_log_file.py -q` → 순차 재실행 **69 passed in 10.50s**, 종료 코드 0.
- 위 부분 스위트의 첫 실행은 전체 스위트와 겹쳐 **68 passed, 1 error**였다. `test_restarting_the_app_does_not_clear_the_puzzle_cache`의 fixture가 공용 테이블을 초기화하는 순간 MySQL 1684 concurrent DDL 오류가 났다. 리뷰어의 중복 실행으로 인한 간섭이므로 제품 결함으로 세지 않았으며, 전체 종료 후 위와 같이 재실행해 전부 통과했다. 전체 스위트 자체에는 실패가 없었다.
- `uv run ruff check .` → **All checks passed!**, 종료 코드 0.
- `uv run flask db heads` → **`b1c7d4e0a932 (head)`**, 정확히 1줄·1개 head.
- 단위/통합 테스트 통과와 별개로 아래 compose의 실제 병합 설정 및 10개 동시 기록 실험에서 MAJOR 3건을 직접 확인했다. 암호화 테스트는 OpenSSL/gzip을 실제 실행하며 Docker·Slack 경계만 스텁이므로 실제 외부 서비스를 호출하지 않는다.


## 결함

### D-36-1 — 인증서 설정이 backup 컨테이너에 전달되지 않아 매일 백업이 실패함

- 심각도: **MAJOR**
- 위치: `docker-compose.prod.yml:114` (backup environment), `scripts/backup.sh:64` (필수 설정 검사).
- 재현: 실제 자격정보 없이 예제 설정만으로 아래 명령을 실행한다. 컨테이너를 띄우거나 NAS에 접속하지 않는다.

```sh
ENV_FILE=.env.prod.example docker compose -f docker-compose.prod.yml \
  --env-file .env.prod.example config --format json |
  uv run python -c 'import json,sys; s=json.load(sys.stdin)["services"]; print(s["backup"]["environment"].get("BACKUP_ENCRYPTION_CERT_FILE", "MISSING"))'
```

- 기대: 예제에 선언된 인증서 경로 `/backups/backup-cert.pem`이 backup 환경에 들어간다.
- 실제: `MISSING`. backup에는 `env_file`도 없고 해당 environment 항목도 없다. Compose의 `--env-file`은 선언하지 않은 값을 컨테이너로 자동 전달하지 않는다. `backup.sh`는 이 값이 비면 덤프 생성 전에 종료한다. 따라서 문서대로 인증서를 배치하고 env를 채워도 매일 백업이 실패한다(Slack 값이 있으면 실패 알림만 발생).
- 테스트 누락: 스크립트 테스트는 인증서 환경변수를 직접 주입하므로 운영 compose의 전달 누락을 잡지 못한다.

### D-36-2 — Gunicorn 로그가 공유 볼륨 밖에 기록되어 회전·보관되지 않음

- 심각도: **MAJOR**
- 위치: `docker-compose.prod.yml:55`, `docker-compose.prod.yml:70`, `gunicorn.conf.py:23`.
- 재현: 위 compose config 명령의 JSON에서 `services.app.environment.LOG_DIR`, `services.app.volumes`, `services.backup.environment`를 확인한다.
- 기대: 호스트 `./logs`를 `/logs`로 마운트하고 app·backup 모두 컨테이너 내부 `/logs/access.log`를 사용한다.
- 실제: 예제 prod 설정에서 app은 `LOG_DIR=./logs`를 env_file로 받으며 마운트 target은 `/logs`다. Dockerfile의 WORKDIR가 `/srv`이므로 Gunicorn은 `/srv/logs/access.log`에 쓴다. backup은 LOG_DIR를 전달받지 않아 `/logs/access.log`만 회전한다. develop의 `./logs-develop`과 RELEASE가 권하는 호스트 절대 경로도 같은 불일치가 발생한다.
- 영향: 로그는 app 컨테이너 파일시스템에 남아 재생성 때 사라지며, 보관 기간 자동 삭제·일 회전도 적용되지 않는다. 방침의 1년 보관 약속과 다르다.
- 테스트 누락: `tests/test_access_log_file.py`는 마운트 문자열과 독립 Gunicorn 설정만 검사하고, env_file까지 합쳐진 컨테이너 경로를 비교하지 않는다.

### D-36-3 — 동시 감사 기록이 중복 키 오류로 유실됨

- 심각도: **MAJOR**
- 위치: `app/repositories/access_log_repository.py:33`, `app/access_log.py:103`.
- 재현: 실제 테스트 MySQL에서 동일 스키마를 별도 검증 테이블로 매핑하고 변경 없는 `record_access`/`append`를 10개 스레드로 동시에 호출했다. 기존 pytest 테이블과 충돌하지 않도록 이름만 분리했으며 완료 후 테이블을 제거했다. 아래 코드는 이미 설정한 `TEST_DATABASE_URL`/`TEST_REDIS_URL`을 사용하는 `uv run python`에서 실행할 수 있다(테스트 DB에서만 실행).

```python
import threading
from sqlalchemy import MetaData
from sqlalchemy.orm import registry
from app import create_app
from app.extensions import db
from app.models import AccessLog
from app.repositories import access_log_repository as repo
from app.services import access_log_service as svc

app = create_app('testing')
table = AccessLog.__table__.to_metadata(MetaData(), name='_review36_access_log')
class Probe:
    pass
registry().map_imperatively(Probe, table)
repo.AccessLog = svc.AccessLog = Probe
with app.app_context():
    table.create(db.engine)
    try:
        for seeded in (False, True):
            db.session.execute(table.delete())
            db.session.commit()
            def record(actor):
                svc.record_access(action='me.history.read', actor=actor,
                                  remote_ip='127.0.0.1', target=None, status_code=200)
            if seeded:
                record('guest.seed')
            barrier = threading.Barrier(10)
            errors = []
            def worker(i):
                with app.app_context():
                    barrier.wait()
                    try:
                        record(f'guest.{i}')
                    except Exception as exc:
                        errors.append((type(exc).__name__, exc.orig.args[0]))
                    finally:
                        db.session.remove()
            threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            print(seeded, db.session.query(Probe).count(), errors)
            db.session.remove()
    finally:
        table.drop(db.engine)
```

- 기대: 빈 체인은 10행, 기존 1행이 있으면 총 11행, 오류 0건.
- 실제 1차: 빈 체인 3행/오류 7건, 기존 체인 총 5행/오류 6건. 독립 재실행 2차: 각각 2행/오류 8건, 총 4행/오류 7건. 모두 `IntegrityError`/MySQL 1062였다.
- 원인과 영향: 마지막 행에 대한 `SELECT ... FOR UPDATE`만으로 다음 연결점을 안정적으로 직렬화하지 못한다. 같은 `prev_hash`를 사용하는 INSERT의 unique 충돌을 재시도하지 않으며, 응답 훅은 예외를 로깅한 뒤 원래 응답을 반환한다. 체인이 갈라지지는 않지만 개인정보 처리 요청의 감사 기록 자체가 사라진다. 빈 테이블에만 한정된 문제가 아니다.
- 테스트 누락: 기존 동시성 테스트는 seed 뒤 두 스레드 한 번뿐이다. README의 “GET_LOCK으로 한 줄씩 쌓는다” 설명도 현재 구현과 다르다.

## 범위·보안·참고

- 공유 문서는 README 설계 판단 §36, env의 36 항목, RELEASE §36을 추가했다. §16 및 스펙 미정 27·16 글머리 변경은 티켓의 명시적 예외 범위다. 별도 무단 범위 확장은 발견하지 않았다.
- 새 개인키·토큰·운영 비밀번호 값의 커밋은 발견하지 않았다. 공개키 생성 명령·예제·마스킹 값은 실제 시크릿으로 보지 않았다. `.gitignore`·`.dockerignore`에는 기본 로그 폴더 제외가 있다. 변경은 인증/CSRF 가드를 제거하지 않는다.
- 법적 페이지는 본문 문구만 바뀌었고 레이아웃·CSS·디자인 토큰 변경은 없다. 스타일 제안은 결함으로 올리지 않았다.
- 고시 조문은 구현 문서가 인용한 기준과의 일치만 검토했다. 문서 자체가 남긴 현행 조문 확인 및 NAS 키 보관·배포 리허설·월간 점검은 사람 확인 사항이며 이번 로컬 리뷰가 실행 완료를 인증하지 않는다.
- 결함 집계: BLOCKER 0, MAJOR 3, MINOR 0.

판정: FAIL
