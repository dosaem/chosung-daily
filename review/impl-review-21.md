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
