"""Gunicorn 설정 — 웹 요청 접근 로그를 파일로 남긴다(티켓 36).

Gunicorn 기본값은 "접근 로그 없음" 이다. 개인정보의 안전성 확보조치 기준
(개인정보보호위원회 고시 제2023-6호) 제8조가 개인정보처리시스템의 접속기록을
1년 이상 보관하도록 해서, DB 감사 로그(`app/access_log.py`)와 별개로 **모든 요청**
을 파일로 모은다. 회전·gzip·만료 삭제는 backup 컨테이너의 cron 이
`scripts/rotate-access-log.sh` 로 한다.

Dockerfile CMD 에 `--access-logfile ${LOG_DIR}/access.log` 를 쓰지 않고 이 파일을
둔 이유: exec 형식 CMD 는 셸을 거치지 않아 `${LOG_DIR}` 이 그대로 문자열로 들어간다.
설정 파일이면 파이썬이 env 를 읽고, 포맷 문자열도 테스트가 읽을 수 있다
(`tests/test_access_log_file.py`).

**포맷에서 Authorization 헤더·쿠키·쿼리스트링을 뺀다.** 지금은 게스트 토큰이 헤더로,
백업 코드가 본문으로 오기 때문에 URL 에 비밀값이 없지만, 포맷이 `%(r)s`(요청 줄
전체)나 `%(q)s` 를 담고 있으면 나중에 쿼리로 뭔가를 받는 순간 1년 보관되는 파일로
조용히 새어 나간다.
"""

import contextlib
import os

LOG_DIR = os.environ.get("LOG_DIR", "/logs")

# 못 만들면 Gunicorn 이 파일을 열 때 바로 죽는다 — 접속기록이 조용히 빠지는 쪽보다
# 배포 시점에 멈추는 쪽이 낫다(`docs/RELEASE.md` "### 36." 의 LOG_DIR 메모).
with contextlib.suppress(OSError):
    os.makedirs(LOG_DIR, exist_ok=True)

accesslog = f"{LOG_DIR}/access.log"
# 오류·기동 로그는 그대로 컨테이너 표준 출력이다(`docker logs` 로 본다).
errorlog = "-"
access_log_format = '%(h)s %(t)s "%(m)s %(U)s" %(s)s %(b)s "%({user-agent}i)s" %(L)s'

# SIGTERM(배포 교체) 뒤 진행 중 요청을 마칠 시간. compose 의 stop_grace_period(20초)
# 보다 짧아야 gunicorn 이 스스로 정리를 끝낸다 — 정답 제출이 중간에 끊겨 attempt 만
# 남는 일을 막는다(티켓 50).
graceful_timeout = 15
