# 티켓 47 조사 — 무중단 배포 (2026-10-16)

## 지금 (deploy/deploy.sh)

`compose up -d --build` 한 줄이 빌드와 교체를 같이 한다. 순서는 ① 이미지 빌드(NAS 에서
수 분, 이 동안 옛 컨테이너가 계속 서비스) → ② app·worker·beat 컨테이너 stop → start
→ ③ `flask db upgrade` → ④ /health 200 확인.

- **끊기는 구간**: ② 의 stop~gunicorn 기동 (~5–10초). 그동안 Cloudflare 터널이
  127.0.0.1:8089 에 못 붙어 502.
- **순서 문제**: 마이그레이션(③)이 새 코드 기동(②) **뒤**다. 새 코드가 새 열을 읽는
  마이그레이션이면 기동~업그레이드 사이에 500 이 난다. 지금까진 Beat 가 자정에만
  쓰는 테이블이라 안 터졌을 뿐이다.
- 빌드 실패면 교체 전에 멈추니 그 점은 이미 안전하다.

## 1단계 — 지금 바로 (티켓 47 범위 제안): "빌드 먼저, 마이그레이션 먼저, 교체는 마지막"

스크립트만 바꾼다. 인프라 변경 없음.

```
compose build                      # 옛 컨테이너 그대로 서비스 중
compose run --rm --no-deps app uv run flask db upgrade   # 새 이미지로 마이그레이션(확장만)
compose up -d --no-build app worker beat                 # 교체 — 여기만 ~5초
```

- 끊김은 그대로 ~5초지만 **마이그레이션 뒤 기동**이라 "새 코드가 없는 열을 읽는"
  창이 사라진다. 전제: 마이그레이션은 expand 만(열 삭제·이름 변경은 두 배포로 나눔).
  이 규칙은 이미 README §02 expand–contract 판단과 같다.
- `app` 에 `stop_grace_period: 15s` 와 gunicorn `graceful_timeout` 을 두면 진행 중
  요청은 끝까지 처리한 뒤 죽는다(정답 제출이 중간에 끊겨 attempt 만 남는 일 방지).
- worker 는 `celery worker` 가 SIGTERM 에 warm shutdown 이라 진행 중 태스크(LLM
  호출 포함)를 마치고 내려간다. beat 는 상태가 Redis/DB 에 없어도 되니 그냥 교체.

## 2단계 — 나중에: 롤링 교체 (끊김 0초, cloudflared 는 안 건드림)

호스트 포트 하나에 컨테이너 하나가 묶여 있어서(`127.0.0.1:8089:5000`) 같은 포트로
새 app 을 띄울 수 없다 — 이게 compose 로 롤링이 안 되는 유일한 이유다.

- compose 에 **리버스 프록시 하나(Caddy)** 를 넣고 8089 는 Caddy 가 잡는다. Caddy 가
  `app:5000` 으로 보내고 도커 DNS 로 레플리카를 동적으로 찾는다.
- 배포: `up -d --scale app=2 --no-recreate`(새 이미지로 2번째) → 새 컨테이너 /health
  200 확인 → 옛 컨테이너 `stop` → `up -d --scale app=1`. Caddy 는 죽은 업스트림을
  자동으로 건너뛴다.
- cloudflared(NAS 호스트, 경로 20개 공용)는 그대로 127.0.0.1:8089 — 손대지 않는다.
- 비용: 컨테이너 1개(Caddy, ~30MB), compose 수정, 스크립트 분기. develop 도 같은
  구조라 테스트는 develop 에서 먼저.

## 3단계 — 안 함: blue/green 두 프로젝트

prod-blue/prod-green 두 compose 프로젝트를 두고 Cloudflare 경로 포트를 API 로
바꾸는 방식. mysql/redis 를 별도 "infra" 프로젝트로 떼서 external network 로 공유해야
하고(볼륨 이동 포함), 배포마다 Cloudflare API 호출이 든다. 2단계로 끊김 0초가 되니
단일 NAS 취미 앱에서 이만한 재구성은 값어치가 없다. README 에는 "검토했고 안 한
이유" 로만 남긴다.

## 결정 필요 (사용자)

1. 1단계를 티켓 47 로 바로 진행할지 (스크립트·compose 소폭, 테스트 `tests/test_deploy_script*` 갱신).
2. 2단계(Caddy 롤링)를 지금 같이 할지, 출시 뒤로 미룰지. 권장: 출시 뒤.
