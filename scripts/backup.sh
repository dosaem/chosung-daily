#!/bin/bash
# MySQL 덤프 1회. backup 컨테이너의 backup-cron.sh 가 매일 04:00 KST 에 부른다.
# 수동 실행: docker compose -p <프로젝트> exec backup /scripts/backup.sh
#
# env: MYSQL_HOST(기본 mysql) MYSQL_DATABASE(기본 chosung_daily) MYSQL_ROOT_PASSWORD
#      DUMP_DIR(기본 /backups) BACKUP_RETENTION_DAYS(기본 14) SLACK_WEBHOOK_URL(없으면 알림 생략)
# -E: ERR trap 을 함수 안에서도 받는다(아래 trap 이 모든 실패를 알림으로 보낸다).
set -Eeuo pipefail

MYSQL_HOST="${MYSQL_HOST:-mysql}"
MYSQL_DATABASE="${MYSQL_DATABASE:-chosung_daily}"
DUMP_DIR="${DUMP_DIR:-/backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"

log() { echo "[backup] $(date '+%Y-%m-%d %H:%M:%S%z') $*"; }

# 실패를 운영자가 알아야 한다 — Slack 이 안 되더라도 종료 코드는 그대로 1.
notify_slack() {
  [ -n "$SLACK_WEBHOOK_URL" ] || return 0
  # 메시지에 따옴표·개행을 넣지 않는다(JSON 을 printf 로 만든다).
  curl -sS -m 10 -X POST -H 'Content-type: application/json' \
    --data "$(printf '{"text":"%s"}' "$1")" "$SLACK_WEBHOOK_URL" >/dev/null || true
}

notified=0
fail() {
  # ERR trap 과 명시적 fail 이 겹쳐도 알림은 한 번만 간다.
  if [ "$notified" -eq 0 ]; then
    notified=1
    log "FAILED: $1"
    notify_slack "[chosung-daily] MySQL backup failed - db=$MYSQL_DATABASE host=$MYSQL_HOST - $1"
  fi
  exit 1
}

# mkdir·mv·보존 정리처럼 `set -e` 가 그 자리에서 죽여버리는 단계도 반드시 알림을
# 거치게 한다. 이게 없으면 저장 경로·용량·권한 문제로 그 날 백업이 통째로 없어도
# 운영자는 Slack 을 못 받고(로그만 남는다) cron 루프는 다음 날로 넘어간다.
# 아래에 메시지를 직접 주는 fail 들이 있고, 이 trap 은 그 밖의 모든 실패를 받는다.
trap 'fail "unexpected error at ${BASH_SOURCE[0]##*/}:$LINENO (exit $?)"' ERR

# 비밀번호를 인자로 넘기면 같은 호스트의 `ps` 에 그대로 보인다 — 600 권한 임시
# 파일로 넘기고 종료할 때(성공·실패·중단 모두) 지운다.
cnf="$(mktemp)"
chmod 600 "$cnf"
trap 'rm -f "$cnf" "${tmp_dump:-}"' EXIT
printf '[client]\npassword=%s\n' "${MYSQL_ROOT_PASSWORD:-}" >"$cnf"

mkdir -p "$DUMP_DIR" || fail "cannot create dump dir $DUMP_DIR"
stamp="$(date '+%Y%m%d-%H%M%S')"
dump="$DUMP_DIR/$MYSQL_DATABASE-$stamp.sql.gz"
# 덤프 도중 컨테이너가 죽으면 반쪽 파일이 "그 날의 백업" 으로 남는다. 임시
# 이름으로 쓰고 끝까지 성공했을 때만 제 이름으로 옮긴다.
tmp_dump="$dump.partial"

log "dumping $MYSQL_DATABASE from $MYSQL_HOST -> $dump"
# --single-transaction: InnoDB 를 테이블 잠금 없이 한 시점으로 뜬다(04:00 에도
#   누가 플레이할 수 있다). --databases + --add-drop-database: 덤프 안에
#   CREATE/DROP DATABASE 가 들어가서 복구가 "덤프 시점 그대로" 가 된다
#   (복구 후에 덤프 이후 생긴 행이 남지 않는다).
if ! mysqldump \
  "--defaults-extra-file=$cnf" \
  -h "$MYSQL_HOST" -u root \
  --single-transaction --quick --add-drop-database \
  --databases "$MYSQL_DATABASE" | gzip -c >"$tmp_dump"; then
  fail "mysqldump exited non-zero"
fi

[ -s "$tmp_dump" ] || fail "dump is empty"
mv "$tmp_dump" "$dump" || fail "cannot move dump into place: $dump"
log "wrote $(du -h "$dump" | cut -f1) $dump"

# 보존 N일 = 오늘 것까지 N개. `-mtime +$((N-1))` 는 "N일보다 더 오래된 것",
# 즉 04:00 에 돌 때 N일 전 덤프가 지워지고 N개가 남는다.
# 정리가 안 되면 디스크가 차서 다음 백업부터 실패한다 — 덤프는 떴더라도 알린다.
if ! find "$DUMP_DIR" -maxdepth 1 -type f -name "$MYSQL_DATABASE-*.sql.gz" \
  -mtime "+$((BACKUP_RETENTION_DAYS - 1))" -print -delete |
  while read -r old; do log "pruned $old"; done; then
  fail "retention prune failed in $DUMP_DIR (dump $dump is written)"
fi

log "done ($(find "$DUMP_DIR" -maxdepth 1 -type f -name '*.sql.gz' | wc -l | tr -d ' ') dumps kept)"
