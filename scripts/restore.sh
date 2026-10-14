#!/bin/bash
# 덤프 하나를 지정 compose 프로젝트의 MySQL 에 복원한다. 되돌릴 수 없다.
#
#   scripts/restore.sh [-y] [-k <개인키.pem>] <덤프.sql.gz.enc|덤프.sql.gz> [compose 프로젝트명]
#
# 덤프는 공개키(CMS 봉투)로 암호화돼 있다(`scripts/backup.sh`, 티켓 36) — 복호화
# 개인키는 NAS 에 두지 않으므로 복구할 때 `-k` 나 `BACKUP_DECRYPTION_KEY_FILE` 로
# 그 자리에서 넘긴다. **개인키를 잃으면 모든 백업을 복구할 수 없다**(docs/RELEASE.md
# "### 36." 의 키 보관 절차). 암호화 전에 뜬 평문 `.sql.gz` 덤프도 당분간 그대로
# 복원된다 — 그 덤프가 보존 기간이 지나 사라지면 평문 경로를 뺀다.
#
# 프로젝트명을 안 주면 환경변수 COMPOSE_PROJECT_NAME 을 쓴다(prod 는
# chosung-daily-prod, develop 은 chosung-daily-develop — docs/RELEASE.md 표).
# 덤프에 DROP/CREATE DATABASE 가 들어 있어서(backup.sh 의 --add-drop-database)
# 복원하면 덤프 시점 이후 생긴 행은 사라진다.
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
cd "$(cd "$(dirname "$0")/.." && pwd)"

usage() {
  echo "사용법: scripts/restore.sh [-y] [-k <개인키.pem>] <덤프.sql.gz.enc> [compose 프로젝트명]" >&2
  exit 2
}

assume_yes=0
key_file="${BACKUP_DECRYPTION_KEY_FILE:-}"
while [ $# -gt 0 ]; do
  case "$1" in
  -y)
    assume_yes=1
    shift
    ;;
  -k)
    key_file="${2:-}"
    [ -n "$key_file" ] || usage
    shift 2
    ;;
  *) break ;;
  esac
done

dump="${1:-}"
project="${2:-${COMPOSE_PROJECT_NAME:-}}"

[ -n "$dump" ] || usage
[ -f "$dump" ] || {
  echo "덤프 파일이 없다: $dump" >&2
  exit 1
}
[ -n "$project" ] || {
  echo "compose 프로젝트명을 인자나 COMPOSE_PROJECT_NAME 으로 줘야 한다" >&2
  usage
}

# 암호화 덤프(`.sql.gz.enc`)는 개인키가 있어야 한 글자도 못 읽는다. 키가 없거나
# 틀린 걸 MySQL 을 건드린 뒤에 알게 되면 "복구 실패" 가 멀쩡한 DB 를 날린다 —
# 그래서 확장자를 보고 먼저 막고, 아래 무결성 검사도 복호화까지 통과시켜 본다.
encrypted=0
case "$dump" in
*.enc)
  encrypted=1
  [ -n "$key_file" ] || {
    echo "암호화된 덤프다 — 복호화 개인키가 필요하다: -k <개인키.pem> 또는 BACKUP_DECRYPTION_KEY_FILE" >&2
    exit 1
  }
  [ -f "$key_file" ] || {
    echo "복호화 개인키 파일이 없다: $key_file" >&2
    exit 1
  }
  ;;
esac

# 복호화 결과를 파일로 떨어뜨리지 않는다 — 평문 덤프가 디스크에 남으면 암호화
# 보관의 의미가 없다. 두 번 부른다(무결성 검사 + 실제 복원).
dump_stream() {
  if [ "$encrypted" -eq 1 ]; then
    openssl cms -decrypt -binary -inform DER -inkey "$key_file" -in "$dump"
  else
    cat "$dump"
  fi
}

# 아래 복원은 `gzip -dc | mysql` 스트리밍이다 — 끝이 잘린 덤프여도 앞쪽의
# DROP/CREATE DATABASE 가 mysql 에 먼저 닿아 그대로 실행된다. 그러면 "복구
# 실패" 가 멀쩡하던 DB 를 날리는 결과가 된다(긴 덤프면 일부 테이블만 복원된
# 상태로 남는다). -t 는 압축을 끝까지 풀어보기만 하고 아무것도 출력하지 않으니,
# DB 를 건드리기 전에 여기서 끝낸다.
dump_stream | gzip -t || {
  echo "덤프를 끝까지 읽지 못했다(복호화 또는 gzip 무결성 검사 실패) — MySQL 은 건드리지 않았다: $dump" >&2
  [ "$encrypted" -eq 1 ] && echo "키가 맞는지 확인: $key_file" >&2
  exit 1
}

if [ "$assume_yes" -ne 1 ]; then
  # 파이프·CI 에서 모르고 돌아가면 안 된다 — tty 가 아니면 -y 를 요구한다.
  [ -t 0 ] || {
    echo "비대화 실행에서는 -y 를 줘야 한다 (대상: $project)" >&2
    exit 1
  }
  printf '%s 의 MySQL 을 %s 로 덮어쓴다. 되돌릴 수 없다. 계속할까? [y/N] ' "$project" "$dump"
  read -r answer
  case "$answer" in
  y | Y | yes) ;;
  *)
    echo "취소했다" >&2
    exit 1
    ;;
  esac
fi

echo "[restore] $dump -> project=$project ($COMPOSE_FILE)"
# 비밀번호는 mysql 컨테이너 안의 env 를 그대로 쓴다 — 호스트 스크립트가 시크릿을
# 읽거나 인자로 넘기지 않는다(쉘에서 '...' 로 묶어 호스트 확장을 막는다).
dump_stream | gzip -dc |
  docker compose -f "$COMPOSE_FILE" -p "$project" exec -T mysql \
    sh -c 'exec mysql -u root -p"$MYSQL_ROOT_PASSWORD"'

# Redis 는 MySQL 과 같이 되감기지 않는다. 복구 전 DB 에서 만들어진 파생 키가
# 남으면 앱이 복원된 DB 대신 그걸 읽는다 — 오늘 퍼즐 캐시(`puzzle:<날짜>`, TTL
# 26시간)는 복구 전 정답을 계속 내놓고, 그 퍼즐 id 가 복원된 DB 에 없으면 제출이
# FK 오류로 깨진다. 통계·리더보드(`stats:`/`lb:`) 카운터도 되감긴 attempt 행을
# 세고 있던 값이라 복원된 DB 보다 앞서 있다. app/worker/beat 를 재시작해도 안
# 지워진다 — Redis 는 별도 컨테이너고 캐시는 그 안에 있다.
# FLUSHDB 는 안 쓴다: 같은 Redis DB 에 celery 브로커 큐와 rate limit 카운터가
# 산다(둘 다 DB 와 무관하므로 되감을 이유도 없다).
echo "[restore] Redis 파생 키 정리 (puzzle:/stats:/lb:)"
docker compose -f "$COMPOSE_FILE" -p "$project" exec -T redis sh -c '
  set -eu
  deleted=0
  for pattern in "puzzle:*" "stats:*" "lb:*"; do
    # SCAN 을 `for key in $(...)` 에 바로 넣으면 안 된다 — 치환이 죽어도 for 는
    # 빈 목록을 돌고 넘어가서, Redis 가 안 떠 있는 것과 "지울 키가 없다" 가
    # 똑같이 보인다(set -e 도 치환 실패를 못 잡는다). 단순 대입이면 set -e 가
    # 치환의 종료 코드에 반응하니, 먼저 변수로 받는다.
    keys=$(redis-cli --scan --pattern "$pattern")
    [ -n "$keys" ] || continue
    for key in $keys; do
      # set -eu 로 DEL 실패도 여기서 끊긴다 — 못 지운 키를 세고 넘어가면
      # 복구 전 값이 남은 채로 성공을 선언하게 된다.
      redis-cli del "$key" >/dev/null
      deleted=$((deleted + 1))
    done
  done
  echo "[restore] deleted $deleted derived keys"
' || {
  echo "Redis 파생 키를 못 지웠다 — 앱이 복원된 DB 대신 복구 전 캐시를 내보낼 수 있다." >&2
  echo "직접 확인하고 지워야 한다:" >&2
  echo "  docker compose -f $COMPOSE_FILE -p $project exec redis \\" >&2
  echo "    sh -c 'redis-cli --scan --pattern \"puzzle:*\"'" >&2
  exit 1
}

echo "[restore] 완료 — MySQL 은 덤프 시점으로, Redis 파생 키는 비워졌다."
