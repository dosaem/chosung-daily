#!/bin/bash
# backup 컨테이너의 entrypoint. 매일 BACKUP_AT(기본 04:00) 에 backup.sh 를 부른다.
# 컨테이너 TZ=Asia/Seoul 이라 로컬 시각 = KST.
#
#   /scripts/backup-cron.sh                # 루프
#   /scripts/backup-cron.sh --print-next   # 다음 실행 시각만 출력(테스트·점검용)
#
# cron 데몬을 안 쓴다: mysql 이미지에 cron 이 없어서 컨테이너가 뜰 때마다
# 패키지를 받아와야 하고(네트워크 의존), crond 가 죽으면 백업이 조용히 멈춘다.
# "다음 04:00 까지 자고 일어나서 덤프" 는 PID 1 이 직접 하니 죽으면 compose 의
# restart 정책이 컨테이너를 다시 띄운다.
set -euo pipefail

BACKUP_AT="${BACKUP_AT:-04:00}"
here="$(cd "$(dirname "$0")" && pwd)"

# 오늘의 BACKUP_AT 이 이미 지났으면 내일 같은 시각. date 산술 없이 하루 안의
# 초 단위로만 계산해서 GNU/BSD date 차이를 피한다(KST 는 DST 가 없다).
seconds_until_next() {
  local target_h="${BACKUP_AT%%:*}" target_m="${BACKUP_AT##*:}"
  local target=$((10#$target_h * 3600 + 10#$target_m * 60))
  local now
  now=$((10#$(date '+%H') * 3600 + 10#$(date '+%M') * 60 + 10#$(date '+%S')))
  local wait=$((target - now))
  [ "$wait" -gt 0 ] || wait=$((wait + 86400))
  echo "$wait"
}

if [ "${1:-}" = "--print-next" ]; then
  wait="$(seconds_until_next)"
  printf '%s:00 %s (in %ss)\n' "$BACKUP_AT" "$(date '+%z')" "$wait"
  exit 0
fi

echo "[backup-cron] daily at $BACKUP_AT $(date '+%z'), next in $(seconds_until_next)s"
while true; do
  sleep "$(seconds_until_next)"
  # backup.sh 가 실패해도(Slack 알림은 거기서 쏜다) 루프는 계속 돈다 —
  # 하루 실패가 다음 날 백업까지 멈추게 하지 않는다.
  "$here/backup.sh" || echo "[backup-cron] backup.sh failed, continuing"
done
