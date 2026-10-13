# 티켓 21 최종 리뷰 — 라운드 1

- 검토일: 2026-10-14
- 기준: 로컬 `main` = `feb2553ec7ad1f5255dfccda2dfd633b1f04180a`, 구현 HEAD = `bd6fdfe2b25d1ca4c05038edf18b9b22a9aac4c7`.
- `git log main..HEAD`의 `fef1317`, `131097f`, `bd6fdfe` 및 `git diff main...HEAD` 전체 변경 12개 파일을 검토했다.
- 요구사항: `.scratch/store-launch/issues/21-backup-restore.md`, 스펙 §C.28 및 US 62·63. 구현 증거 `review/impl-evidence-21.md`는 참고하되 실행 결과와 구분했다. UI 변경은 없어 디자인 검토는 해당 없다.
- 결함: BLOCKER 0 / MAJOR 3 / MINOR 0.

## 티켓 체크박스별 확인

| 체크박스 | 충족 여부 | 직접 확인한 근거 및 제한 |
|---|---|---|
| 독립 백업 서비스, 04:00 KST, mysqldump/gzip, 14일 정리, BACKUP_DIR bind mount 및 예시 env, root/DSM 메모 | 충족 | compose의 독립 `backup`, `TZ=Asia/Seoul`, `BACKUP_AT=04:00`, `${BACKUP_DIR:-./backups}:/backups`, 양쪽 예시 env를 확인했다. 스크립트 실행 테스트에서 gzip 생성·14일 경계 정리·다음 실행 시각 검사가 통과했다. RELEASE의 DSM 메모도 존재한다. 스케줄러는 cron 데몬 대신 sleep 루프이며 그 판단이 README에 기록돼 있다. 실제 NAS 권한·04:00 장기 실행은 이번 리뷰에서 검증하지 않았다. |
| 실패 시 curl로 SLACK_WEBHOOK_URL 알림 | 미충족 | mysqldump 실패 테스트는 통과하지만 디렉터리 생성·최종 파일 이동·정리 실패는 알림 경로를 우회한다(D-21-1). |
| restore.sh가 지정 덤프를 지정 compose 프로젝트 MySQL에 복원 | 미충족 | 정상 gzip의 SQL 전달 및 `-p` 대상 선택 테스트는 통과한다. 손상된 gzip을 검증하기 전에 파괴적 SQL이 전달돼 복구 실패가 기존 데이터 손상으로 이어질 수 있다(D-21-2). |
| 로컬 백업 → 변경 → 복구 → 원복 확인, RELEASE 복구 리허설 절차·결과 | 증거 부족 | RELEASE에 절차와 과거 실측 결과는 있다. 이번 리뷰에서는 기본 공유 테스트 DB 오류가 두 차례 발생하여 실제 MySQL 왕복 복원은 독립 재검증하지 못했다. 또한 문서의 캐시 정리 명령은 실제로 Redis 캐시를 제거하지 않는다(D-21-3). |
| README 운영 절에 위치·보존·복구 명령 | 충족 | README 111행부터 운영 표와 복구 명령이 있다. 다만 뒤따르는 캐시 정리 명령은 D-21-3의 수정 대상이다. |

## 직접 실행한 검증

| 명령 | 결과 |
|---|---|
| `TEST_REDIS_URL=redis://127.0.0.1:6379/15 uv run pytest tests/test_backup_restore.py -q` | 26 passed, 2.32초 |
| `TEST_REDIS_URL=redis://127.0.0.1:6379/15 uv run pytest -q` | 2 failed, 78 passed, 35 errors, 22.39초 |
| `TEST_REDIS_URL=redis://127.0.0.1:6379/15 uv run pytest -q --tb=no` (한 번 재실행) | 1 failed, 60 passed, 53 errors, 8.96초 |
| `uv run ruff check .` | All checks passed |
| `bash -n scripts/backup.sh scripts/backup-cron.sh scripts/restore.sh` | 종료 코드 0 |
| `git diff --check main...HEAD` | 종료 코드 0 |

로컬 MySQL/Redis 컨테이너는 실행 중이었다. `TEST_DATABASE_URL`을 별도로 지정하거나 새 DB를 만들지 않았으며 레포 기본 `chosung_daily_test`와 Redis DB 15를 사용했다. 전체 테스트에서 테이블 부재(`guest_stats` 등), setup/teardown SQL 오류가 발생하고 재실행마다 실패 분포가 달라 공유 DB 병렬 사용 충돌이 의심된다. 다른 프로세스가 원인인지는 확정하지 않았고, 이 실패를 티켓 21의 회귀 결함으로 단정하지 않았다. 전체 테스트 통과라는 구현 증거의 주장은 이번 리뷰에서 재확인되지 않았다.

마이그레이션 변경이 없으므로 `flask db heads` 확인 대상이 아니다. 새 테스트는 셸을 실행하고 gzip/find를 실제 사용해 의미가 있지만, mysqldump/docker/curl은 스텁이다. 실제 DB 복원, 손상 입력, 파일시스템 실패의 알림, Redis 복구 일관성까지 검증한다고 볼 수 없다. NAS·배포·외부 서비스 접근 및 실제 Slack 전송은 하지 않았다.

## 결함 목록

### D-21-1 — 파일시스템 실패가 Slack 알림 없이 종료됨

- 심각도: **MAJOR**
- 위치: `scripts/backup.sh:38`, `scripts/backup.sh:59`, `scripts/backup.sh:64` (오류 처리: 25–28행).
- 요구: 티켓 두 번째 체크박스 및 §C.28의 백업 실패 Slack 알림.
- 재현: 아래 공통 재현 코드의 `mkdir failure` 실행. 임시 일반 파일 아래를 `DUMP_DIR`로 지정하고 curl은 호출 기록만 남기는 스텁으로 실행했다.
- 기대: 디렉터리 준비 실패도 종료 코드 비정상 및 Slack 호출 1회.
- 실제: 종료 코드 1, `slack called: False`. `set -e`가 즉시 종료하고 EXIT trap은 파일 삭제만 한다. `fail()`은 dump 파이프라인/크기 검사에서만 호출된다. `mv`·보존 정리 실패도 같은 구조다.
- 영향: 저장 경로·용량·권한 문제로 백업이 실패해도 운영자는 요구된 알림을 받지 못한다. cron 루프는 로그만 남기고 다음 날로 넘어간다. 실패 단계 전반에 알림 처리가 필요하다.

### D-21-2 — 손상된 압축 덤프가 검증 전에 기존 DB를 파괴할 수 있음

- 심각도: **MAJOR**
- 위치: `scripts/restore.sh:59`.
- 재현: 아래 코드에서 DROP/CREATE DATABASE SQL의 gzip 끝 8바이트를 제거하고 `restore.sh -y`에 전달했다. docker 스텁은 stdin을 기록하므로 실제 DB는 건드리지 않는다.
- 기대: 손상된 gzip을 대상 MySQL 실행 전에 거부하고 기존 DB에 SQL을 전달하지 않는다.
- 실제: gzip은 `unexpected end of file`로 종료 코드 1을 반환하지만, docker stdin에는 이미 `DROP DATABASE IF EXISTS chosung_daily;`와 `CREATE DATABASE chosung_daily;`가 전달됐다.
- 영향: 실제 클라이언트는 스트리밍된 DDL을 즉시 실행하므로 pipefail이 최종 실패를 알려도 원래 DB는 이미 삭제될 수 있다. 긴 덤프의 중간 절단이라면 일부 테이블/행만 복원된다. 최소한 압축 전체 무결성 검사를 DB 변경 전에 마쳐야 한다. 현재 복구 테스트는 정상 gzip만 사용한다.

### D-21-3 — 복구 후 캐시 정리 안내가 Redis의 복구 전 데이터를 남김

- 심각도: **MAJOR**
- 위치: `docs/RELEASE.md:144`, `README.md:131`, `scripts/restore.sh:63`.
- 근거: `app/services/puzzle_cache.py:11`의 TTL은 26시간이며, `app/services/puzzle_service.py:28`은 Redis 히트 시 DB를 읽지 않는다. `app/extensions.py:17`은 새 Redis 연결만 생성한다.
- 재현 입력: Redis DB 15에서 `cache_puzzle()`로 2099-12-21의 테스트 퍼즐(id 212121)을 저장한 뒤, 별도 `create_app('testing')` 인스턴스에서 `get_cached_puzzle()`을 호출했다. 결과는 기존 id 212121, TTL 93600초였다. 검증 후 해당 키만 삭제했다. 실제 서비스 재시작은 실행하지 않았고 앱 재생성으로 초기화 동작을 확인했다.
- 운영 재현: 백업 A 이후 오늘 퍼즐 B가 Redis에 캐시된 상태 → MySQL을 A로 복원 → 문서대로 `restart app worker beat` → 오늘 퍼즐 조회.
- 기대: 복구된 MySQL의 퍼즐 A를 읽는다.
- 실제: 안내 명령은 Redis 키를 지우지 않으므로 B가 남는다. 동일 id이면 잘못된 정답으로 판정할 수 있고, 복원 DB에 없는 id이면 쓰기 오류가 날 수 있다. Redis는 별도 서비스이며 앱 재시작과 무관하게 살아 있다.
- 조치 방향: 대상 프로젝트의 파생 Redis 데이터 무효화를 복구 절차에 명시하고, 변경된 퍼즐을 캐시한 후 복원하는 리허설을 검증해야 한다. 현재 증거의 오답 횟수 복원은 이 경우를 다루지 않는다.

## D-21-1 / D-21-2 안전 재현 코드

레포 루트에서 `uv run python`으로 아래 코드를 실행했다. 임시 파일과 PATH 스텁만 사용하며 실제 Docker·MySQL·Slack 호출은 없다.

```python
import gzip
import os
import pathlib
import subprocess
import tempfile

root = pathlib.Path.cwd()
with tempfile.TemporaryDirectory() as td:
    p = pathlib.Path(td)
    b = p / "bin"
    b.mkdir()
    calls = p / "calls"
    for name, body in {
        "curl": 'echo called >> "$CALLS"',
        "mysqldump": 'echo "DROP DATABASE IF EXISTS chosung_daily;"',
        "docker": 'cat > "$SQL_CAPTURE"',
    }.items():
        f = b / name
        f.write_text("#!/bin/sh\n" + body + "\n")
        f.chmod(0o755)
    env = {
        **os.environ,
        "PATH": str(b) + ":" + os.environ["PATH"],
        "CALLS": str(calls),
        "SQL_CAPTURE": str(p / "sql"),
        "SLACK_WEBHOOK_URL": "https://example.invalid",
        "DUMP_DIR": str(p / "not-directory" / "dumps"),
    }
    (p / "not-directory").write_text("x")
    r = subprocess.run([str(root / "scripts/backup.sh")],
                       env=env, capture_output=True, text=True)
    print("mkdir failure:", r.returncode, "slack called:", calls.exists())
    data = gzip.compress(b"DROP DATABASE IF EXISTS chosung_daily;\n"
                         b"CREATE DATABASE chosung_daily;\n")
    bad = p / "corrupt.sql.gz"
    bad.write_bytes(data[:-8])
    r = subprocess.run([str(root / "scripts/restore.sh"), "-y",
                        str(bad), "review-local"],
                       env=env, capture_output=True, text=True)
    print("truncated dump:", r.returncode,
          "SQL passed to mysql:", (p / "sql").read_text().strip())
    print("gzip error:", r.stderr.strip())
```

## 범위·보안·공유 파일 확인

- README 설계 판단은 `### 21.`로 기존 절 끝에 추가했고, RELEASE 및 예시 env도 자기 번호 절을 추가했다. 기존 다른 티켓의 행/절 변경은 발견하지 않았다.
- `.gitignore`·`.dockerignore`의 기본 백업 경로 제외는 덤프 유출 방지를 위한 티켓 범위 내 변경이다.
- 앱 인증·CSRF 경로 변경은 없다. 복구 대상 프로젝트 필수 입력, 비대화 `-y` 요구, 백업 인증 임시 파일 600 권한 및 삭제 처리를 확인했다.
- diff에서 실제 키·토큰·비밀번호 값이 기록된 정황은 발견하지 않았다. 테스트의 명시적 더미 및 증거의 예시 URL은 실제 자격증명으로 판단하지 않았다.
- 취향·스타일 결함은 등록하지 않았다. 이번 리뷰는 애플리케이션·테스트·설정·`.scratch/`를 변경하지 않았다.

판정: FAIL

## 라운드 2

- 검토일: 2026-10-14. 로컬 `main`: `491418fb4b7b3ebae9a0205443381456ef4821f9`, 구현 HEAD: `8f2fcb3bb32a24c44c0bba1f760413be8dc38220`.
- `git diff main...HEAD` 전체 13개 파일 및 `git log main..HEAD`의 6개 커밋(`f48eb99`, `0326d52`, `541dc18`, `7af1a11`, `4e7f5aa`, `8f2fcb3`)을 확인했다. origin/main은 사용하지 않았다.
- 티켓 21, 스펙 §C.28·US 62/63, CONTEXT, 이전 리뷰 및 구현 증거를 읽었다. UI 변경은 없어 디자인 검토는 해당 없다.
- 현재 열린 결함: **BLOCKER 0 / MAJOR 1 / MINOR 0**. 이전 3건은 FIXED, 새 결함 D-21-4를 등록한다.

### 체크박스별 확인

| 티켓 체크박스 | 판정 | 직접 확인한 근거와 제한 |
|---|---|---|
| 독립 백업 서비스, 매일 04:00 KST, gzip, 14일 정리, BACKUP_DIR bind mount·예시 env, DSM ACL 메모 | 충족 | compose 105–124행의 독립 서비스·TZ·시각·보존·bind mount, 양쪽 env의 21번 절, RELEASE의 root/DSM 메모를 확인했다. 전체 테스트에 포함된 실제 셸/gzip/find/date 검사가 통과했다. cron 대신 sleep 루프라는 설계 판단이 README에 있다. NAS ACL 및 장기 스케줄 실행은 직접 검증하지 않았다. |
| 실패 시 curl과 SLACK_WEBHOOK_URL로 알림 | 충족 | backup.sh 41·50·67·71·80행에서 오류를 알림으로 전달한다. mysqldump·mkdir·mv·정리 실패 회귀 테스트가 통과했다. curl은 스텁이며 실제 Slack을 호출하지 않았다. |
| 지정 덤프를 지정 compose 프로젝트 MySQL에 복원 | 미충족 | 정상 SQL 전달·프로젝트 선택·확인 요구 및 손상 gzip 사전 차단은 통과한다. 새 Redis 후처리가 실패해도 성공을 선언해 복구 전 캐시를 남길 수 있다(D-21-4). |
| 로컬 백업 → 변경 → 복원 → 원복 검증과 RELEASE 절차·결과 | 증거 부족 | RELEASE에 A→B→A 절차·수치가 있고 구현 증거에는 수정 후 리허설도 있다. 이번 리뷰는 기본 테스트 DB의 전체 테스트와 별도 셸/Redis 검증을 실행했지만 실제 MySQL 덤프 왕복은 재실행하지 않았다. 기존 실행 기록만으로 독립 재검증 완료라고 판단하지 않는다. |
| README 운영 절의 위치·보존·복구 명령 | 충족 | README 운영 절에 요구된 표와 명령이 있다. Redis 후처리 성공 보장의 실제 한계는 D-21-4에 기록한다. |

### 이전 결함 판정

| ID | 라운드 2 판정 | 근거 |
|---|---|---|
| D-21-1 (MAJOR) | **FIXED** | backup.sh:41의 ERR trap과 50·71·80행의 명시적 실패 처리. 디렉터리 준비·파일 이동·보존 정리 실패 테스트에서 비정상 종료 및 curl 호출을 검증하며 모두 통과했다. |
| D-21-2 (MAJOR) | **FIXED** | restore.sh:44에서 gzip 전체 검사를 MySQL 실행 전에 수행한다. 잘린 gzip 및 일반 텍스트 입력 회귀 테스트가 Docker 호출 자체가 없음을 확인하며 통과했다. |
| D-21-3 (MAJOR) | **FIXED** | restore.sh:82에 같은 프로젝트 Redis의 파생 키 삭제가 추가되고 README/RELEASE의 재시작 안내도 수정됐다. 실제 Redis DB 15의 고유한 검증 키로 추출한 셸 루프를 실행해 puzzle/stats/lb 3개 삭제와 ratelimit 키 보존을 확인했다. 정상 정리는 고쳐졌지만 새 후처리의 오류 전파는 별개 결함 D-21-4다. |

### 직접 실행한 검증

| 명령/검증 | 결과 |
|---|---|
| `TEST_REDIS_URL=redis://127.0.0.1:6379/15 uv run pytest -q --tb=short` | **145 passed in 45.48s**, 종료 0. 티켓 21 테스트 37개 포함. |
| `uv run ruff check .` | **All checks passed!**, 종료 0 |
| `bash -n scripts/backup.sh scripts/backup-cron.sh scripts/restore.sh` | 종료 0 |
| `git diff --check main...HEAD` | 종료 0 |
| 아래 D-21-4 안전 재현 | Redis SCAN 오류 3회에도 restore 종료 0 및 완료 메시지 출력 |
| 실제 로컬 Redis 정상 정리 | `deleted 3 derived keys`, 존재 여부 puzzle/stats/lb/ratelimit = `[0, 0, 0, 1]` |

DB는 레포 기본 `chosung_daily_test`를 사용했다. TEST_DATABASE_URL을 덮어쓰거나 새 DB를 만들지 않았고 Redis만 DB 15로 지정했다. 이번 전체 테스트는 첫 실행에 통과하여 병렬 DB 충돌에 따른 재실행은 없었다. 로컬 MySQL/Redis 컨테이너도 실행 중이었다. 마이그레이션 변경이 없으므로 `flask db heads`는 대상이 아니다.

Redis 정상 정리 검증은 restore.sh의 내부 셸 본문을 추출하고 패턴을 이번 검증에서 만든 고유 키 3개로 좁혀 실행했다. redis-cli 대신 같은 SCAN/DEL을 실제 `127.0.0.1:6379/15`에 수행하는 임시 Python 어댑터를 사용했다. 검증 뒤 남긴 키를 모두 삭제했다. 앞선 Docker exec 경유 시도는 삭제 0개로 나와 정상 동작 증거로 채택하지 않았으며, 위 검증은 실제 compose 왕복을 증명하지 않는다.

### 새 결함

#### D-21-4 — Redis 명령 실패를 무시하고 복구 성공을 선언함

- 심각도: **MAJOR**.
- 위치: `scripts/restore.sh:82`, `scripts/restore.sh:85`, `scripts/restore.sh:86`, `scripts/restore.sh:90` (성공 선언 99행).
- 재현 입력: 유효한 gzip 덤프, MySQL 전달 성공, Redis 서비스의 셸은 실행되지만 redis-cli SCAN이 연결 오류로 종료 1인 상황. 아래 스텁은 외부/DB 접속 없이 실제 restore.sh와 내부 `sh -c`를 실행한다.
- 기대: Redis 정리 실패를 감지해 종료 코드 비정상, 92행의 수동 확인 안내, 완료 메시지 없음.
- 실제: stderr에 연결 오류 3회가 출력되지만 `deleted 0 derived keys` 및 `완료 — MySQL 은 덤프 시점으로, Redis 파생 키는 비워졌다.`가 출력되고 **종료 코드 0**이다.
- 원인: 내부 `sh -c`는 오류 중단을 켜지 않았고 SCAN을 `for key in $(...)` 안에 넣어 상태를 확인하지 않는다. DEL 실패 역시 무시하고 삭제 수를 증가시킨다. 마지막 echo가 성공해 외부 `||` 실패 처리에 도달하지 않는다. 단순히 내부 `set -e`만 추가해도 for의 명령 치환 실패는 별도 확인이 필요하다.
- 영향: 일시적 Redis 연결 실패 등으로 오래된 캐시가 남았는데 운영자는 복구 성공으로 판단한다. Redis 회복 후 복구 전 퍼즐·정답을 읽거나 복원 DB에 없는 퍼즐 ID로 제출 오류가 발생할 수 있다. 구현 증거의 “지우기에 실패하면 종료 코드 1” 주장은 이 재현과 다르다.
- 테스트 한계: `tests/test_backup_restore.py:304`의 docker 스텁은 인자와 stdin을 기록할 뿐 내부 Redis 셸을 실행하지 않는다. 395행 부근의 패턴 포함 검사와 FLUSHDB 금지 검사는 오류 전파를 검증하지 못하며 이 결함이 있어도 통과한다. SCAN/DEL 각각의 실패를 실행하는 회귀 검증이 필요하다.

레포 루트에서 실행한 안전 재현 코드:

```python
import gzip
import os
import pathlib
import subprocess
import tempfile

root = pathlib.Path.cwd()
with tempfile.TemporaryDirectory() as td:
    p = pathlib.Path(td)
    b = p / "bin"
    b.mkdir()
    bodies = {
        "docker": '''case " $* " in
*" exec -T mysql "*) cat >/dev/null;;
*" exec -T redis "*) while [ "$1" != sh ]; do shift; done; exec "$@";;
esac
''',
        "redis-cli": '''echo "Could not connect to Redis: Connection refused" >&2
exit 1
''',
    }
    for name, body in bodies.items():
        f = b / name
        f.write_text("#!/bin/sh\n" + body)
        f.chmod(0o755)
    dump = p / "dump.sql.gz"
    dump.write_bytes(gzip.compress(b"SELECT 1;\n"))
    result = subprocess.run(
        [str(root / "scripts/restore.sh"), "-y", str(dump), "review-local"],
        env={**os.environ, "PATH": str(b) + ":" + os.environ["PATH"]},
        capture_output=True, text=True, check=False,
    )
    print("exit:", result.returncode)
    print(result.stdout)
    print(result.stderr)
```

### 범위·보안·공유 파일

- README 설계 판단·RELEASE·예시 env는 자기 번호 21의 절을 추가했다. 다른 티켓 행을 덮어쓴 변경은 없고 운영 절 추가는 티켓의 명시적 요구다.
- .gitignore/.dockerignore의 덤프 제외는 티켓 범위 안이다. 애플리케이션 인증·CSRF 코드는 변경하지 않았다.
- 프로젝트 필수 입력, 비대화 `-y`, gzip 검사, 백업 인증 임시 파일 600 권한과 정리를 확인했다. 변경 파일에서 실제 시크릿 값이 커밋된 정황은 찾지 못했다. 문서에 자격증명 값을 옮기지 않았다.
- NAS·배포·외부 서비스 호출·push·하위 에이전트 실행은 하지 않았다. 애플리케이션·테스트·설정·.scratch는 수정하지 않았으며 이번 소유 파일은 이 리뷰 문서뿐이다.
- 취향·스타일 제안은 결함으로 등록하지 않았다.

판정: FAIL

## 라운드 3

- 검토일: 2026-10-14. 로컬 `main` = `4f9f1799cade063b5adde4618ab1e3214d3f0446`, 구현 HEAD = `277717bed6e985b54a64975a90355c4b4e2dae83`.
- `git diff main...HEAD`의 13개 파일과 `git log main..HEAD`의 9개 커밋을 확인했다. origin/main은 사용하지 않았다.
- 티켓 21, 스펙 §C.28·US 62/63, CONTEXT, 이전 두 라운드 리뷰, 구현 증거를 대조했다. UI 변경은 없어 디자인 검토 대상이 아니다.
- 열린 결함: **BLOCKER 0 / MAJOR 0 / MINOR 0**. 이전 D-21-1~4는 모두 FIXED이며 REPEAT 및 새 결함은 없다.

### 티켓 체크박스별 확인

| 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| 독립 백업 서비스, 04:00 KST, mysqldump/gzip, 14일 보존, BACKUP_DIR bind mount·예시 env, DSM ACL 메모 | 충족 | `docker-compose.prod.yml:104`부터 독립 서비스·TZ·시각·보존·bind mount가 있다. 양쪽 환경 예시의 21번 절과 RELEASE의 root/DSM 설명을 확인했다. 셸/gzip/find/date 실행 테스트와 실제 MySQL 덤프 생성이 통과했다. cron 데몬 대신 동일 일일 시각을 계산하는 sleep 루프를 사용한다는 판단이 README에 명시돼 있다. |
| 실패 시 curl로 SLACK_WEBHOOK_URL 알림 | 충족 | `scripts/backup.sh:41,50,67,71,80`의 실패 전달을 확인했다. mysqldump·디렉터리 생성·최종 이동·보존 정리 실패 회귀 테스트가 비정상 종료와 curl 호출을 검증하며 통과했다. 실제 Slack 호출은 하지 않았다. |
| 지정 덤프를 지정 compose 프로젝트의 MySQL로 복원 | 충족 | `scripts/restore.sh:34,44,49,69,82`에서 프로젝트 필수·gzip 사전 검사·확인·MySQL 복원·Redis 후처리를 확인했다. 프로젝트 인자 전달 테스트, 실제 DB 왕복, Redis 정상 삭제 및 SCAN/DEL 실패 전파 테스트가 통과했다. |
| 로컬 백업 → 데이터 변경 → restore.sh → 원복 검증, RELEASE에 절차·결과 기록 | 충족 | RELEASE의 `### 21.`에 복구 리허설 절차·실측 결과가 있다. 이번 리뷰에서도 기존 전용 DB에서 실제 backup.sh/restore.sh를 실행하여 A→B→A를 확인했다. 테스트 자원에 연결하기 위한 전송 어댑터의 범위와 제한은 아래에 명시한다. |
| README 운영 절에 위치·보존·복구 명령 | 충족 | `README.md:129`부터 위치·파일명·보존·알림 표와 수동 백업/복구 명령, Redis 파생 키 정리 설명이 있다. |

### 이전 결함 판정

| ID / 기존 심각도 | 판정 | 파일:라인 및 재현 → 기대 / 이번 실제 결과 |
|---|---|---|
| D-21-1 / MAJOR | **FIXED** | `scripts/backup.sh:41,50,71,80`. mkdir·mv·find 정리 실패를 주입 → 비정상 종료와 Slack 호출이 기대되며 해당 회귀 테스트 모두 통과했다. 정상 백업에서는 알림을 보내지 않는다. |
| D-21-2 / MAJOR | **FIXED** | `scripts/restore.sh:44`. gzip footer가 잘린 덤프 또는 일반 텍스트 입력 → MySQL에 SQL을 보내기 전에 실패해야 하며, 해당 테스트가 Docker 호출 없음과 비정상 종료를 확인했다. |
| D-21-3 / MAJOR | **FIXED** | `scripts/restore.sh:82,90,95`. 복구 전 puzzle/stats/lb 키와 ratelimit 키를 심고 복원 → 파생 키만 없어져야 하며 실제 Redis DB 9에서 존재 여부 `[0,0,0,1]`을 확인했다. 문서의 앱 재시작 안내도 직접 삭제 방식으로 수정돼 있다. |
| D-21-4 / MAJOR | **FIXED** | `scripts/restore.sh:83,90,95,100`. Redis 내부 셸은 실행하되 SCAN 또는 DEL이 종료 1을 반환 → 복구 비정상 종료·완료 메시지 없음이 기대되며 `tests/test_backup_restore.py:494,506`이 모두 통과했다. SCAN을 단순 대입으로 받아 `set -eu`가 종료 상태를 검사하고, DEL 실패도 성공 echo 이전에 중단된다. |

회귀 재현 명령은 아래 전체 테스트 또는 동일한 TEST_DATABASE_URL/TEST_REDIS_URL 설정에서 `uv run pytest tests/test_backup_restore.py -q`이다. D-21-4만 확인하려면 `-k 'redis_scan_cannot_run or deleting_a_derived_key_fails or deletes_every_derived_key'`를 덧붙일 수 있다. 새 `redis_exec_stub`은 인자 검사만 하는 기존 docker 스텁과 달리 실제 `sh -c` 본문을 실행하므로 이전 오류를 관측한다.

### 직접 실행한 검증

| 명령/검증 | 결과 |
|---|---|
| 전용 TEST_DATABASE_URL과 `TEST_REDIS_URL=redis://127.0.0.1:6379/9` 설정 후 `uv run pytest -q --tb=short` | **186 passed in 87.12s**, 종료 0. 티켓 21 테스트 40개 포함. |
| `uv run ruff check .` | **All checks passed!**, 종료 0 |
| `bash -n scripts/backup.sh scripts/backup-cron.sh scripts/restore.sh` | 종료 0 |
| `git diff --check main...HEAD` | 종료 0 |
| `uv run flask db heads` | `4e72a4045fbc (head)` 한 줄. 티켓 21 자체의 마이그레이션 변경은 없다. |
| `uv run python /tmp/t21-r3-roundtrip.py` — 아래 실제 로컬 왕복 검증 | 백업 0 / 복원 0, A 원복 및 Redis 선택 삭제 확인 |

TEST_DATABASE_URL은 구현 증거와 `.env.example`의 로컬 접속 형식을 사용하되 DB 이름을 `chosung_daily_test_t21`로 지정했다. 자격증명은 이 문서에 기록하지 않는다. 지정 DB에 정상 연결되어 기본 테스트 DB로 폴백하거나 새 DB를 준비하지 않았다. 기존 전용 마이그레이션 테스트 DB도 전체 테스트에서 재사용했다. 첫 실행에 통과하여 병렬 충돌 재시도는 필요하지 않았다.

#### 실제 MySQL/Redis 왕복 검증과 한계

전체 테스트 종료 후 기존 로컬 `chosung-daily-mysql-1`의 `chosung_daily_test_t21`만 대상으로 다음을 실행했다. 어댑터와 덤프는 임시 디렉터리에 두었고 애플리케이션/테스트 파일은 수정하지 않았다.

1. `t21_r3_probe(id INT PRIMARY KEY, value VARCHAR(10))` 테이블에 `(1,'A')`를 삽입했다.
2. `MYSQL_DATABASE=chosung_daily_test_t21`, 임시 DUMP_DIR, 빈 SLACK_WEBHOOK_URL로 실제 `scripts/backup.sh`를 실행했다. 실제 mysqldump 출력이 gzip 파일로 생성됐고 종료 0이었다.
3. 값을 B로 변경하고 `(2,'new')`를 추가했다. SELECT 결과는 `1 B / 2 new`였다. Redis DB 9에 `puzzle:t21-r3`, `stats:t21-r3`, `lb:t21-r3`, `ratelimit:t21-r3` 네 키를 심었다.
4. 실제 `scripts/restore.sh -y <생성된 덤프> review-local`을 실행했다. 종료 0, `deleted 3 derived keys` 및 완료 메시지가 출력됐다.
5. SELECT 결과는 **`1 A` 한 행**이었다. 추가 행은 없어졌다. 네 Redis 키의 존재 여부는 **`[0,0,0,1]`**이었다.
6. 검증 테이블과 남은 검증 키를 제거했고 임시 덤프도 삭제했다.

전송 어댑터는 `mysqldump`를 기존 로컬 MySQL 컨테이너에서 실행하도록 연결했다(호스트 임시 인증 파일/호스트 옵션 대신 컨테이너 내부 환경 사용, 덤프의 single-transaction/quick/add-drop-database/databases 옵션은 그대로 전달). restore의 Docker 호출은 `review-local` 프로젝트 인자를 확인한 후 기존 로컬 mysql/redis 컨테이너의 실제 exec로 연결했고, Redis 내부 셸의 `redis-cli`에만 `-n 9`를 추가했다. DB·SQL 덤프·gzip·복원·SCAN·DEL은 실제 실행했으며 데이터 응답은 스텁하지 않았다. **prod compose 전체 기동이나 네트워크/마운트 구성을 다시 리허설한 것은 아니다.** 프로젝트 선택과 compose 설정은 별도 테스트 및 정적 대조로 확인했다. NAS ACL, 실제 Slack 수신, 실제 04:00 장시간 대기는 이번 실행 검증 범위 밖이다.

### 범위·보안·공유 파일 확인

- README 설계 판단, RELEASE 및 환경 예시는 21번 절을 추가했다. 다른 티켓의 기존 행/절 삭제 또는 덮어쓰기는 diff에서 발견하지 않았다. README 운영 절과 덤프 ignore 추가도 티켓 범위 안이다.
- 앱 인증/CSRF 경로 변경은 없다. 복원 대상 프로젝트 필수, 비대화 확인, gzip 사전 검사, 백업 인증 임시 파일 권한 600과 종료 시 정리를 확인했다. 실제 시크릿이 변경 파일에 추가된 정황은 발견하지 않았다.
- 셸 테스트의 mysqldump/curl/docker 스텁 한계를 실제 로컬 DB/Redis 왕복으로 보완했다. 외부 전송을 수행하지 않았으며 정상/실패 양쪽 경로의 실행 결과를 확인했다.
- 프로덕션·NAS·배포·외부 서비스 호출·push·하위 에이전트 실행은 하지 않았다. 이번 저장소 수정은 `review/impl-review-21.md`뿐이다.
- 취향·스타일 제안 및 새 결함은 없다.

판정: PASS
