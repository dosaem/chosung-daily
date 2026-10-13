// 자정에 요청이 몰리는 상황을 흉내낸다: 다들 새로고침해서 오늘의 퍼즐을 보고
// (GET /puzzles/today), 그중 일부가 바로 정답을 제출한다(POST .../guesses).
//
// 실행: k6 run k6/midnight_spike.js -e BASE_URL=http://localhost:8000
//
// 캐시 적용/미적용 비교는 이 스크립트를 그대로 두 번 돌려서 한다 —
// (1) docker compose에서 redis를 내린 상태(캐시 조회가 전부 실패해서 DB로
//     폴백, app/utils/redis_safe.py의 safe_redis_call 경로)
// (2) redis를 올린 상태(puzzle:{date} 캐시가 워밍된 상태)
// 코드를 바꿔서 캐시를 끄는 게 아니라, Redis 장애 시 자동 폴백하는 실제 운영
// 동작을 그대로 이용한 것 — docs/perf.md에 방법론 적어둠.
import http from "k6/http";
import { check, sleep } from "k6";
import { Counter, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const TOKEN_COUNT = parseInt(__ENV.TOKEN_COUNT || "60", 10);

// 409(이미 5회 다 씀/이미 정답)와 429(rate limit)는 게임 규칙상 정상적인 응답이지,
// k6가 기본으로 "실패"로 세는 4xx가 아니다 — 안 그러면 http_req_failed가 뻥튀기된다.
http.setResponseCallback(http.expectedStatuses(200, 201, 400, 409, 429));

export const options = {
  scenarios: {
    midnight_spike: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "10s", target: 50 }, // 자정 알림 보고 다들 몰려드는 구간
        { duration: "30s", target: 50 }, // 유지
        { duration: "10s", target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
  },
};

const todayTrend = new Trend("today_duration");
const guessTrend = new Trend("guess_duration");
const unexpectedErrors = new Counter("unexpected_errors");

export function setup() {
  const tokens = [];
  for (let i = 0; i < TOKEN_COUNT; i++) {
    const res = http.post(`${BASE_URL}/api/v1/guests`);
    if (res.status !== 201) {
      throw new Error(`게스트 발급 실패 (setup): ${res.status} ${res.body}`);
    }
    tokens.push(JSON.parse(res.body).token);
  }
  return { tokens };
}

export default function (data) {
  const token = data.tokens[__VU % data.tokens.length];
  const headers = { Authorization: `Bearer ${token}` };

  const todayRes = http.get(`${BASE_URL}/api/v1/puzzles/today`, { headers });
  todayTrend.add(todayRes.timings.duration);
  const todayOk = check(todayRes, { "today 200": (r) => r.status === 200 });
  if (!todayOk) {
    unexpectedErrors.add(1);
    sleep(1);
    return;
  }

  // 30% 정도만 바로 정답을 제출 (자정 스파이크엔 다들 일단 보기부터 한다).
  // 길이는 오늘 퍼즐에 맞춰서 만든다 — 어차피 틀린 단어지만, 길이가 안 맞으면
  // 400(VALIDATION_ERROR)으로 바로 걸러져서 실제 판정 로직을 안 타게 된다.
  if (Math.random() < 0.3) {
    const length = todayRes.json("length") || 2;
    const guess = "가".repeat(length);
    // 퍼즐 고정 — 방금 조회한 퍼즐의 ID 를 같이 보내야 409 PUZZLE_CHANGED 로
    // 걸러지지 않고 실제 판정 경로를 탄다.
    const puzzleId = todayRes.json("puzzle_id");

    const guessRes = http.post(
      `${BASE_URL}/api/v1/puzzles/today/guesses`,
      JSON.stringify({ puzzle_id: puzzleId, guess }),
      { headers: { ...headers, "Content-Type": "application/json" } }
    );
    guessTrend.add(guessRes.timings.duration);

    // 200(판정 성공), 409(이미 5회 다 씀/이미 정답), 429(rate limit)는 전부
    // 정상적인 응답이다 — 그 외만 예상 밖의 에러로 센다.
    const guessOk = check(guessRes, {
      "guess 200/409/429": (r) => [200, 409, 429].includes(r.status),
    });
    if (!guessOk) {
      unexpectedErrors.add(1);
    }
  }

  sleep(1);
}
