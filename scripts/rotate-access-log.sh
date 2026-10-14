#!/bin/bash
# 웹 요청 접근 로그(`${LOG_DIR}/access.log`) 일 회전 + gzip + 보관 기간 지난 것 삭제.
# backup 컨테이너의 backup-cron.sh 가 매일 백업 직후에 부른다(새 컨테이너를 만들지
# 않는다 — 이미 매일 도는 루프가 있다).
#
#   /scripts/rotate-access-log.sh
#
# env: LOG_DIR(기본 /logs) ACCESS_LOG_RETENTION_DAYS(기본 365, 고시 제8조 제1항의
#      법정 최소 기간) SLACK_WEBHOOK_URL(없으면 알림 생략)
#
# **회전은 cp + 비우기(copytruncate)다.** 앱 컨테이너의 Gunicorn 이 이 파일을 열어둔
# 채라서, `mv` 로 옮기면 그 뒤 요청이 사라진 inode 로 흘러가 접속기록이 빠진다. 다른
# 컨테이너의 프로세스에 USR1(로그 재열기)을 보낼 수도 없다 — 그래서 내용만 복사하고
# 원본을 0 바이트로 비운다(logrotate 의 copytruncate 와 같은 방식). 비우는 순간의
# 요청 한두 건이 섞일 수 있다는 게 이 방식의 알려진 대가다.
set -Eeuo pipefail

LOG_DIR="${LOG_DIR:-/logs}"
ACCESS_LOG_RETENTION_DAYS="${ACCESS_LOG_RETENTION_DAYS:-365}"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"

live="$LOG_DIR/access.log"

log() { echo "[rotate-access-log] $(date '+%Y-%m-%d %H:%M:%S%z') $*"; }

notify_slack() {
  [ -n "$SLACK_WEBHOOK_URL" ] || return 0
  curl -sS -m 10 -X POST -H 'Content-type: application/json' \
    --data "$(printf '{"text":"%s"}' "$1")" "$SLACK_WEBHOOK_URL" >/dev/null || true
}

notified=0
fail() {
  if [ "$notified" -eq 0 ]; then
    notified=1
    log "FAILED: $1"
    notify_slack "[chosung-daily] access log rotation failed - dir=$LOG_DIR - $1"
  fi
  exit 1
}

trap 'fail "unexpected error at ${BASH_SOURCE[0]##*/}:$LINENO (exit $?)"' ERR

[ -d "$LOG_DIR" ] || fail "log dir $LOG_DIR does not exist (bind mount 확인)"

if [ -s "$live" ]; then
  rotated="$LOG_DIR/access.log-$(date '+%Y%m%d')"
  # 같은 날 두 번 돌아도 앞서 회전한 분량을 잃지 않는다 — 풀어서 뒤에 이어 붙인다.
  if [ -f "$rotated.gz" ]; then
    gzip -dc "$rotated.gz" >"$rotated" || fail "cannot reopen $rotated.gz"
  fi
  cat "$live" >>"$rotated" || fail "cannot copy $live into $rotated"
  # 복사가 끝난 뒤에 비운다. 순서가 반대면 그 날 요청이 통째로 사라진다.
  : >"$live" || fail "cannot truncate $live"
  gzip -f "$rotated" || fail "cannot gzip $rotated"
  log "rotated -> $rotated.gz ($(du -h "$rotated.gz" | cut -f1))"
else
  log "no requests to rotate ($live)"
fi

# 보존 N일 = 오늘 것까지 N개(backup.sh 와 같은 계산).
if ! find "$LOG_DIR" -maxdepth 1 -type f -name 'access.log-*.gz' \
  -mtime "+$((ACCESS_LOG_RETENTION_DAYS - 1))" -print -delete |
  while read -r old; do log "pruned $old"; done; then
  fail "retention prune failed in $LOG_DIR"
fi

log "done ($(find "$LOG_DIR" -maxdepth 1 -type f -name 'access.log-*.gz' | wc -l | tr -d ' ') files kept)"
