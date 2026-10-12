# 오늘의 초성 (chosung-daily)

하루에 한 문제, 초성을 보고 단어를 맞추는 웹 게임의 백엔드.

> 아직 뼈대만 있는 상태입니다. 아키텍처, API 명세, 설계 판단 등 상세 문서는 이후 Phase에서 채웁니다.

## 실행 방법

```bash
cp .env.example .env
docker compose up -d --build
curl http://localhost:8000/health
```

로컬에서 직접 실행:

```bash
uv sync
uv run pytest
uv run ruff check .
```
