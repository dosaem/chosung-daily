#!/usr/bin/env bash
# Alembic head 가 정확히 하나인지 확인한다.
#
# 병렬로 진행되는 마이그레이션 티켓들이 각각 현재 head 위에 리비전을 올리면
# 머지 후 head 가 둘로 갈라지고, `flask db upgrade` 가 "Multiple head revisions"
# 로 멈춘다 (배포 때 발견하면 늦다). CI 와 머지 직전에 이 스크립트로 잡는다.
#
# head 가 여러 개면 나중에 머지되는 쪽의 down_revision 을 먼저 머지된 리비전으로
# 재설정한다.
set -euo pipefail

export FLASK_APP="${FLASK_APP:-wsgi.py}"

heads_output=$(uv run flask db heads)
echo "$heads_output"

head_count=$(printf '%s\n' "$heads_output" | grep -c '(head)' || true)

if [ "$head_count" -ne 1 ]; then
  echo "Alembic head 가 ${head_count} 개다 (1개여야 한다). 뒤에 머지되는 마이그레이션의 down_revision 을 선행 머지 리비전으로 재설정해라." >&2
  exit 1
fi

echo "OK: Alembic head 1개"
