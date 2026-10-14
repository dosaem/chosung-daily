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

## 라운드 2

- 기준: 로컬 `main` = `055b56ce43df639e63a39d096c1e3b43b275ec1d`, 구현 HEAD = `3464ce8aaf1169ea4b813185dec959cc79e5a147`.
- 티켓 36, 스펙 §A.15·C.28·C.33·미정 27, `git diff main...HEAD`, `git log main..HEAD`, 구현 증거 및 라운드 1 결함을 대조했다. `origin/main`은 사용하지 않았다.
- code-review·verification-before-completion 기준으로 직접 검토했다. 사용자 지시에 따라 하위 에이전트 없이 수행했고, 애플리케이션·테스트·설정·`.scratch/`는 수정하지 않았다.

### 체크박스별 판정

| 티켓 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| 백업 암호화 | 충족 | `scripts/backup.sh:60`부터 인증서 누락을 차단하고 덤프·gzip·CMS를 파이프로 연결한다. 실제 OpenSSL 테스트가 암호화 파일 생성·평문 임시 파일 부재·실패 알림·신구 확장자 보존 삭제를 확인한다. 실제 compose 병합 결과에서도 backup 인증서 경로가 전달된다(D-36-1 FIXED). |
| 복구 | 충족 | `scripts/restore.sh:58`부터 키 검사, `dump_stream` 및 전체 gzip 사전 검증 후에만 MySQL 경로를 호출한다. 올바른 키·누락·잘못된 키·손상·평문 전환기 테스트를 포함한 기존 백업/복구 테스트 파일 전체가 통과했다. |
| 키 절차 문서 | 증거 부족 | `docs/RELEASE.md:617`부터 CMS 키 생성·공개 인증서 배치·NAS 밖 두 곳 보관·분실 경고·교체 절차, README 운영 단락은 있다. 다만 `docs/RELEASE.md:672`의 암호화 복구 리허설 실측은 여전히 미완료 체크박스다. 라운드 1과 동일하게 실제 리허설 완료를 인증하지 않는다. |
| 감사 로그 테이블·기록 지점 | 충족 | migration·INSERT 리포지토리·응답 훅·README 행위 표가 연결되어 있다. 실제 요청 테스트가 운영자 라우트·403·계정 삭제·열람·연결·프로필 변경을 기록한다. 실제 MySQL의 빈/기존 체인에 10개 동시 기록을 넣는 테스트가 행 수·오류 없음·체인 정합성을 확인한다(D-36-3 FIXED). |
| 위변조 검출 | 충족 | `row_hash`·`verify_chain` 및 CLI가 실제 DB 중간 행 변경/삭제를 검출한다. 모델에 `updated_at`이 없고 리포지토리에 update/delete 공개 API가 없다. 만료 삭제 뒤 체인 검사도 통과한다. |
| 접근 로그 | 충족 | `gunicorn.conf.py:30`의 파일 출력과 포맷, Dockerfile의 설정 로딩을 확인했다. 인증 헤더·쿠키·쿼리 및 전체 요청 줄을 제외한다. prod/develop 실제 compose config에서 app·backup 모두 동일 호스트 폴더를 `/logs`로 마운트하고 `LOG_DIR=/logs`를 받는다(D-36-2 FIXED). |
| 보관·삭제 | 충족 | 기본 365일 설정, Beat 일일 DB 삭제, backup cron 파일 회전·gzip·만료 삭제 배선이 있다. 기간 안팎의 행/파일과 기간 변경·삭제 실패 알림을 실행 테스트로 확인했다. |
| 점검 | 충족 | 실제 DB 행을 사용하는 CLI 테스트가 월별 행위 수·거부 수·체인 검증 결과 및 잘못된 월 입력을 검증한다. RELEASE §36에 월 1회 실행·결과 보관 체크박스가 있다. |
| 법적 문서 동기화 | 충족 | ko/en 본문, 법적 체크리스트, RELEASE §16→§36 참조, 스펙 미정 27·16 글머리가 구현과 맞게 변경됐다. 법적 페이지·체크리스트 테스트가 통과했다. 시행일은 같은 날짜인 2026-10-14로 유지한 기존 설명을 수용한다. |
| env·README 설계 판단·기존 테스트·ruff | 충족 | 승인된 CMS 환경변수와 LOG_DIR·보관 기간 설명이 있고 README §36에 공개키·두 겹 로그·해시 체인·기간 근거를 기록했다. 백업/복구 테스트 전체 및 ruff를 직접 실행해 통과했다. |

### 이전 결함 재판정

#### D-36-1 — FIXED (이전 MAJOR)

- 위치: `docker-compose.prod.yml:131`, `scripts/backup.sh:60`.
- 재현: 아래 명령을 `.env.prod.example`과 `.env.develop.example` 각각으로 실행해 실제 Docker Compose 병합 결과를 확인했다. 전체 환경을 출력하지 않고 인증서·로그 경로·로그 마운트만 추출했다.

```sh
ENV_FILE=.env.prod.example docker compose -f docker-compose.prod.yml \
  --env-file .env.prod.example config --format json |
  uv run python -c 'import json,sys; s=json.load(sys.stdin)["services"]; print({n:{"LOG_DIR":s[n]["environment"].get("LOG_DIR"), "CERT":s[n]["environment"].get("BACKUP_ENCRYPTION_CERT_FILE"), "mounts":[v for v in s[n]["volumes"] if v["target"]=="/logs"]} for n in ("app","backup")})'
```

- 기대: backup에 `BACKUP_ENCRYPTION_CERT_FILE=/backups/backup-cert.pem` 전달.
- 실제: prod/develop 모두 기대와 일치한다. 기존 `MISSING` 증상은 재현되지 않는다. 스크립트 테스트의 직접 env 주입뿐 아니라 compose 자체의 치환 결과로 수정 여부를 확인했다.

#### D-36-2 — FIXED (이전 MAJOR)

- 위치: `docker-compose.prod.yml:64`, `docker-compose.prod.yml:133`, `docker-compose.prod.yml:142`, `gunicorn.conf.py:23`.
- 재현: D-36-1의 config 명령을 prod/develop 예제 각각에 실행한다.
- 기대: app과 backup의 컨테이너 환경이 모두 `/logs`이며 로그 mount target과 같고, 호스트 source도 서로 같다.
- 실제: prod는 두 서비스 모두 호스트 `logs`→`/logs`, develop은 두 서비스 모두 `logs-develop`→`/logs`이고 `LOG_DIR=/logs`다. 따라서 Gunicorn 출력과 회전 스크립트가 같은 파일을 가리킨다. 호스트 상대 경로가 app의 `/srv` 밑으로 새던 증상은 해소됐다.

#### D-36-3 — FIXED (이전 MAJOR)

- 위치: `app/repositories/access_log_repository.py:44`, `app/repositories/access_log_repository.py:77`, `tests/test_concurrency.py:418`.
- 재현: 전용 테스트 자원을 지정한 상태에서 `uv run pytest tests/test_concurrency.py -q -k access_log`에 해당하는 세 테스트를 아래 통합 실행에 포함했다. 빈 체인/기존 체인 두 경우 모두 barrier로 10개 실제 스레드를 동시에 시작하며 제품 `record_access`·`append`를 그대로 사용한다.
- 기대: 오류 0건, 빈 체인 10행/기존 체인 11행, 체인 검증 이상 없음.
- 실제: 두 10개 동시성 테스트와 기존 2개 동시 기록 테스트가 모두 통과했다. `GET_LOCK`을 전용 연결에서 획득하고 append 커밋 후 같은 연결에서 해제하므로 빈 테이블에도 직렬화가 적용되며, 락 획득 후 READ COMMITTED 조회가 직전 커밋의 꼬리를 읽는다. 기록 경로 또는 DB를 mock한 테스트가 아니다.

### 직접 실행한 검증

- 기존 localhost MySQL `chosung_daily_test_t36`, 기존 마이그레이션 DB `chosung_daily_test_t36_migrations`, localhost Redis DB 10을 각각 `TEST_DATABASE_URL`·`TEST_MIGRATION_DATABASE_URL`·`TEST_REDIS_URL`로 지정했다. 접속 성공했고 기본 DB 폴백이나 새 DB 생성은 없었다. 자격정보 값은 기록하지 않는다.
- 아래 변경 관련 테스트 11개 파일을 **한 프로세스로 순차 실행**했다. 결과는 **427 passed in 396.60s (0:06:36)**, 종료 코드 0이다. 간헐 실패나 재실행은 없었다.

```sh
uv run pytest tests/test_access_log.py tests/test_access_log_file.py \
  tests/test_backup_restore.py tests/test_celery_wiring.py tests/test_cli.py \
  tests/test_compose_config.py tests/test_concurrency.py \
  tests/test_legal_checklist.py tests/test_legal_pages.py \
  tests/test_migrations.py tests/test_sentry.py -q
```

- `uv run ruff check .` → **All checks passed!**, 종료 코드 0.
- `uv run flask db heads` → **`b1c7d4e0a932 (head)`**, 정확히 1줄·1개 head.
- `git diff --check main...HEAD` → 출력 없음, 종료 코드 0.
- 증거 문서의 전체 1353개 통과 주장을 이번 리뷰의 직접 실행 결과로 대체하지 않았다. 이번 라운드에서 직접 재실행한 범위는 위 427개이며 전체 스위트 재실행은 하지 않았다.
- 백업/복구 테스트는 실제 OpenSSL·gzip을 사용하고 외부 Docker/Slack 호출은 스텁이다. 감사 로그·체인·보존·마이그레이션은 실제 전용 MySQL에서 검증하고, Sentry는 메모리 Transport로 검증한다. 실제 외부 서비스·NAS·프로덕션에 접속하지 않았다.

### 범위·보안·참고

- 신규 결함 없음. 이전 결함은 **FIXED 3, REPEAT 0**. 현재 미해결 결함 집계: **BLOCKER 0 / MAJOR 0 / MINOR 0**.
- 공유 파일의 README 설계 판단·env·RELEASE 추가분은 36 항목이며, 기존 §16·법적 문서·스펙 지정 글머리 및 README 운영 설명 변경은 티켓에서 지시한 범위다. 새 무단 범위 확장이나 인증·CSRF 가드 제거, 새 운영 시크릿·키·토큰 값의 커밋을 발견하지 않았다.
- 법적 템플릿은 본문 고지 변경이다. 디자인 SCREENS 및 OVERRIDES 우선 규칙과 대조했으며 레이아웃·CSS·색 토큰 변경은 없다. 취향·스타일 제안은 결함으로 올리지 않았다.
- 키 절차의 실측 증거 부족은 남아 있다. 스펙 검증 범위가 NAS 실행·리허설을 RELEASE의 사람 체크리스트로 구분하고 이번 리뷰가 프로덕션 접근을 금지하므로, 배포 리허설 완료와 코드 리뷰 PASS를 구분한다. `restore.sh` 전체 운영 경로의 암호화 복구 실측, NAS 밖 키 보관, 월간 점검은 출시 담당자가 별도로 확인해야 한다.
- 조문은 레포가 인용한 기준과 구현·고지의 일치를 검토했다. 현행 조문 번호 확인은 RELEASE §36에 남은 사람 확인 항목이며 이번 리뷰가 법적 적합성을 인증하지 않는다.

판정: PASS
