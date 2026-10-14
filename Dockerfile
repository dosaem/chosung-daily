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
CMD ["uv", "run", "gunicorn", "-c", "gunicorn.conf.py", "-b", "0.0.0.0:5000", "wsgi:app"]
