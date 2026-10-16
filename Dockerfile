FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev build-essential pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /srv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 5000

# 접근 로그 설정은 gunicorn.conf.py 에 있다 — exec 형식 CMD 는 셸을 안 거쳐서
# `--access-logfile ${LOG_DIR}/...` 의 env 치환이 안 된다(티켓 36).
# `--no-sync`: 이미지 빌드 때 `uv sync --frozen --no-dev` 로 끝난 환경을 그대로 쓴다. 없으면
# `uv run` 이 기동 때마다 lock 을 다시 맞추려 패키지를 설치한다(2026-10-16 실측 25초,
# 네트워크가 막히면 아예 못 뜬다) — 롤링 교체의 healthy 대기 시간을 그만큼 먹는다.
CMD ["uv", "run", "--no-sync", "gunicorn", "-c", "gunicorn.conf.py", "-b", "0.0.0.0:5000", "wsgi:app"]
