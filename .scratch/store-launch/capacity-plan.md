# 지금 NAS 로 언제까지 버티나 — 용량 예측과 대응 (2026-10-16)

## 지금 (실측)

- NAS: DS423+ (Celeron J4125 4코어 2.0GHz), RAM 17.8GB(업그레이드됨), 볼륨 21TB 중 11TB 사용.
- 컨테이너 56개(알리미·habitopia·fitness·habitit·dosaem-admin 의 dev/prod + chosung prod/develop). 평상시 CPU 는 거의 놀고(각 컨테이너 0~4%), **load average 7 은 거의 전부 IO 대기**(IO 6.8 / CPU 0.2) — 디스크(HDD)가 이미 바쁘다는 뜻. chosung 은 메모리 약 1.2GB(prod: app 176MB·worker 371MB·beat 144MB·mysql 500MB·redis 13MB).
- 앱 서버: gunicorn **sync 워커 1개**(설정 없음 → 기본값). 요청 하나씩 처리.
- 외부 경로: Cloudflare Tunnel(무료, 대역폭 제한 없음) → 집 회선 업링크 → NAS. 정적 파일은 Cloudflare 캐시.
- 부하 실측(`docs/perf.md`, 맥에서): 50 VU 닫힌 모델에서 p95 22ms(캐시) — NAS 는 CPU 가 맥보다 3~4배 느리다고 보면 **워커 1개 ≈ 초당 30~60 요청**이 상한.

## 트래픽 모델 (하루 한 문제 게임의 특성)

플레이어 1명이 하루에 보내는 요청: 오늘 퍼즐 조회 1~3, 제출 1~5, 통계·리더보드 2~4, 설정 1 → **약 10~15 요청/일**. 문제는 총량이 아니라 **자정 스파이크**: 하루 한 문제 게임은 00:00 KST 직후 10분에 하루 트래픽의 20~40% 가 몰린다(Wordle 류 공통). 그래서 "DAU" 가 아니라 "자정 10분 동시 사용자" 로 센다.

| 단계 | DAU | 자정 10분 요청(30% 가정) | 초당 피크 | 지금 NAS(워커 1개) |
|---|---|---|---|---|
| A | 1,000 | 4,500 | ~8/s | 여유 |
| B | 10,000 | 45,000 | ~75/s | **경계** — 워커 1개 상한, 자정에 느려짐 |
| C | 50,000 | 225,000 | ~375/s | 안 됨 — 워커를 늘려도 J4125 4코어 파이썬 상한(~200~300/s) 근처 |
| D | 100,000+ | 450,000+ | ~750/s | NAS 밖으로 |

DB 는 당분간 문제가 아니다: 시도 5행/인/일 → DAU 50,000 이어도 하루 25만 행, 1년 9천만 행 — 인덱스 있으면 MySQL 한 대로 충분하고 디스크 수 GB. Redis 는 더 여유. **먼저 막히는 건 ① 앱 워커 수 ② CPU ③ 이미 바쁜 HDD IO(다른 프로젝트들과 공유) ④ 집 회선·NAS 가 단일 장애점**이다.

## 알아채는 법 (지금 바로 넣을 것)

- Sentry Performance(트랜잭션 샘플링 10%)로 `/puzzles/today`·`guesses` p95 를 본다. **자정 00:00~00:10 p95 > 300ms 가 3일 연속**이면 다음 단계.
- `#chosung-alerts` 로 오는 신호: UptimeRobot 다운, Sentry 에 `WORKER TIMEOUT`/`OperationalError: too many connections`.
- 주 1회 `docker stats` 와 NAS 리소스 모니터(IO 대기)를 본다 — IO 대기가 꾸준히 8 넘으면 다른 프로젝트 포함 HDD 가 한계.

## 대응 — 돈 안 드는 것부터

**1단계 (지금, 0원, 1시간)** — B 단계까지 버티게 한다.
- gunicorn `workers = 3`, `worker_class = gthread`, `threads = 4` → 동시 12 요청. 메모리 +400MB. 롤링 배포라 무중단.
- MySQL `innodb_buffer_pool_size` 256MB → 512MB(데이터가 전부 메모리에), `max_connections` 150.
- Cloudflare 캐시 규칙: `/static/*` 1년, `/` HTML 은 캐시 안 함(게스트별 상태).
- 자정 스파이크 완화: 앱이 00:00 정각이 아니라 **0~60초 랜덤 지연** 뒤 새 퍼즐을 받게(앱 쪽 1줄). 피크가 1/6로 퍼진다.

**2단계 (B→C 사이, 월 2~3만원)** — 앱 서버만 밖으로, DB·백업은 NAS 유지 or 함께 이동.
- 서울 리전 VPS 1대(2 vCPU/4GB, Vultr·Hetzner 아시아·Oracle Free Tier 4코어 ARM 은 0원)에 **지금 compose 그대로**(proxy·app·worker·beat·mysql·redis) 올린다. 배포 스크립트는 `ssh <host>` 만 바뀐다(Tailscale 로 묶으면 Actions 도 그대로).
- 이전 절차: 점검 모드 on → `mysqldump` → VPS 복원 → cloudflared 를 VPS 에 설치해 같은 경로 이름으로 → Cloudflare 경로를 VPS 터널로 바꿈(DNS 변경 없음, 수 초) → 점검 off. NAS 는 develop + 백업 저장소로 남는다(백업은 이미 암호화 덤프라 NAS 로 복사만 추가).
- 기준: 자정 p95 가 1단계 뒤에도 300ms 를 넘거나, NAS IO 대기가 다른 프로젝트까지 느리게 하거나, 집 회선·정전으로 다운이 한 번이라도 나면.

**3단계 (C 이상, 월 5~15만원)** — 돈이 벌리고 있을 때만.
- 앱 2대 + 관리형 MySQL(Naver Cloud / AWS RDS 서울) + 관리형 Redis. Cloudflare Load Balancer 또는 터널 2개(같은 호스트명에 두 커넥터면 자동 분산).
- 리더보드·통계는 이미 Redis 라 수평 확장에 걸리는 게 없다. 자정 배정(Beat)은 **1대만** 돌린다(락은 이미 있음).

**하지 않을 것**: Kubernetes, 서버리스 재작성. 지금 구조(compose + Caddy 롤링)는 VPS 2대까지 그대로 간다.

## 요약 한 줄

**DAU 1만까지는 설정만 바꿔 NAS 로 버티고, 자정 p95 300ms 가 3일 연속이거나 집 회선 때문에 한 번이라도 내려가면 서울 VPS 1대로 compose 째 옮긴다(반나절, 월 2~3만원). DAU 5만 넘어 수익이 나면 앱 2대 + 관리형 DB.**
