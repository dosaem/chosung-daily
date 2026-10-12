# 부하 테스트: 자정 트래픽 스파이크

## 시나리오

`k6/midnight_spike.js`. "자정에 오늘의 퍼즐이 바뀌고 다들 몰려드는 상황"을 흉내낸다.

- VU를 10초 동안 0 → 50으로 올리고, 30초 유지, 10초 동안 내림 (총 50초).
- 매 iteration마다 `GET /api/v1/puzzles/today` (다들 일단 새로고침해서 확인).
- 그중 30%는 바로 `POST /api/v1/puzzles/today/guesses`로 정답 제출 (길이는 오늘
  퍼즐에 맞춰서 생성, 항상 오답).
- `setup()`에서 VU 수보다 많은 게스트 토큰(60개)을 미리 발급해서 VU마다 서로
  다른 게스트로 동작하게 함 — 같은 토큰을 여러 VU가 같이 쓰면 분당 10회
  rate limit에 걸리거나, `GuestStats` 행 잠금(`SELECT ... FOR UPDATE`)에서
  서로 기다리게 돼서 순수 서버 성능이 아니라 우리 쪽 동시성 제어 때문에
  느려지는 것처럼 보인다.
- 200(판정 성공)/409(이미 5회 다 씀 또는 이미 정답)/429(rate limit)는 전부
  정상 응답으로 처리한다 — 게임 규칙상 자연스럽게 나오는 상태라 "실패"로 세면
  안 된다(`http.setResponseCallback`으로 k6 기본 집계에도 반영).

## 실행 방법

```bash
docker compose up -d --build
uv run flask schedule-puzzles --days 7   # 오늘 포함 며칠치 퍼즐 준비

# 캐시 적용 (Redis 워밍된 상태)
curl -s -X POST http://localhost:8000/api/v1/guests | ... # 아무 요청으로 캐시 1회 워밍
k6 run k6/midnight_spike.js -e BASE_URL=http://localhost:8000

# 캐시 미적용 (Redis 자체를 내려서 비교)
docker compose stop redis
k6 run k6/midnight_spike.js -e BASE_URL=http://localhost:8000
docker compose up -d redis
```

캐시를 끄려고 코드를 건드리지 않고 **Redis 컨테이너를 그냥 내렸다** — Phase 4에서
만든 `safe_redis_call` 장애 폴백이 실제로 Redis 없이도 게임이 정상 동작하는지
그대로 보여주는 방식이기도 하다(`GET /puzzles/today`가 캐시 미스마다 DB로
폴백, 응답은 여전히 200).

## 결과

| 지표 | 캐시 미적용 (Redis 다운) | 캐시 적용 (Redis 워밍) | 개선 |
|---|---|---|---|
| `GET /puzzles/today` p95 | 62.39ms | 19.76ms | **약 3.2배** |
| `GET /puzzles/today` 평균 | 27.03ms | 8.87ms | 약 3.0배 |
| `POST .../guesses` p95 | 69.53ms | 24.28ms | 약 2.9배 |
| `POST .../guesses` 평균 | 33.77ms | 11.15ms | 약 3.0배 |
| 전체 `http_req_duration` p95 | 65.31ms | 21.66ms | 약 3.0배 |
| 전체 `http_req_duration` 평균 | 28.24ms | 9.44ms | 약 3.0배 |
| `http_req_failed` | 0% | 0% | - |
| RPS | 51.35/s | 51.56/s | 거의 동일 (아래 설명) |
| 체크 통과율 | 100% (2564/2564) | 100% (2599/2599) | - |

환경: 맥미니 로컬, docker compose(app+mysql+redis+worker+beat 동시 실행),
MySQL 8 / Redis 7 둘 다 컨테이너. 토큰 60개, 최대 동시 VU 50.

## 해석

- **캐시가 지연시간을 ~3배 줄인다.** `GET /puzzles/today`가 캐시 히트일 땐
  DB에 `daily_puzzle` JOIN `word` 한 번 안 가고 Redis GET 한 번으로 끝나는
  구조(`app/services/puzzle_cache.py`)라, MySQL 왕복이 빠지는 만큼 그대로
  줄어든다. `POST .../guesses`도 내부적으로 같은 캐시 조회를 거쳐서 같이
  빨라졌다.
- **RPS는 왜 거의 안 변했나**: 이 테스트는 "VU마다 1초 쉬고 반복"하는
  닫힌 모델(closed model)이라, 요청 속도가 서버 처리 속도가 아니라 **VU 수와
  sleep(1)로 미리 정해져 있다** — 서버가 더 빨라져도 VU는 어차피 1초마다 한
  번씩만 요청한다. 그래서 이 설정에서 캐시 효과는 "같은 요청을 더 빨리
  처리한다"(지연시간 감소)로 나타나지, "초당 더 많이 처리한다"(RPS 증가)로는
  안 나타난다. 서버가 버틸 수 있는 **최대 처리량**을 보려면 VU를 sleep 없이
  최대한 돌리거나, k6의 `constant-arrival-rate`/`ramping-arrival-rate`
  executor(목표 요청 속도를 고정하고 그걸 못 따라가면 지연시간이 터지는 걸
  보는 방식)로 바꿔야 한다 — 이번엔 "자정에 다들 거의 동시에 새로고침"이라는
  현실적인 사용자 행동을 흉내내는 데 집중해서 닫힌 모델로 했다.
- **에러율 0%**: 50 VU, 분당 10회 rate limit, 게스트별 `FOR UPDATE` 잠금
  동시성 제어가 걸려있는 상태에서도 요청이 하나도 안 깨졌다 — 동시성 설계
  (Phase 3)가 부하 아래에서도 버틴다는 간접 증거.
