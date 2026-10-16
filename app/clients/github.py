"""GitHub REST 래퍼 — 운영 이슈(Sentry 에러) 생성·조회·닫기만 한다(티켓 51).

다른 외부 호출(카카오·Slack·Anthropic)과 같은 틀: `requests` + 타임아웃 + 예외 두 종류.
토큰은 `GITHUB_ISSUES_TOKEN`(issues 쓰기 권한만 있는 fine-grained PAT). 로그에 토큰이
새지 않게 예외 메시지에 응답 본문만 담는다.
"""

import requests
from flask import current_app

API_BASE = "https://api.github.com"
TIMEOUT_SECONDS = 10
_RETRYABLE_STATUSES = {429}
_SERVER_ERROR = 500
_CLIENT_ERROR = 400


class GitHubError(Exception):
    def __init__(self, message: str, status_code: int | None = None, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


def _headers() -> dict:
    token = current_app.config["GITHUB_ISSUES_TOKEN"]
    if not token:
        raise GitHubError("GITHUB_ISSUES_TOKEN 이 비어 있습니다.")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _repo_url(path: str) -> str:
    return f"{API_BASE}/repos/{current_app.config['GITHUB_ISSUES_REPO']}{path}"


def _request(method: str, url: str, **kwargs) -> dict | list:
    try:
        response = requests.request(
            method, url, headers=_headers(), timeout=TIMEOUT_SECONDS, **kwargs
        )
    except requests.RequestException as exc:
        raise GitHubError(f"GitHub 연결 실패 ({type(exc).__name__})", retryable=True) from exc
    if response.status_code >= _SERVER_ERROR or response.status_code in _RETRYABLE_STATUSES:
        raise GitHubError(
            f"GitHub {response.status_code}: {response.text[:200]}",
            status_code=response.status_code,
            retryable=True,
        )
    if response.status_code >= _CLIENT_ERROR:
        raise GitHubError(
            f"GitHub {response.status_code}: {response.text[:200]}",
            status_code=response.status_code,
        )
    return response.json() if response.content else {}


def create_issue(title: str, body: str, labels: list[str]) -> dict:
    return _request(
        "POST", _repo_url("/issues"), json={"title": title, "body": body, "labels": labels}
    )


def list_issues(label: str, state: str = "all", per_page: int = 100) -> list[dict]:
    return _request(
        "GET",
        _repo_url("/issues"),
        params={"labels": label, "state": state, "per_page": per_page},
    )


def comment_issue(number: int, body: str) -> dict:
    return _request("POST", _repo_url(f"/issues/{number}/comments"), json={"body": body})


def close_issue(number: int) -> dict:
    return _request(
        "PATCH",
        _repo_url(f"/issues/{number}"),
        json={"state": "closed", "state_reason": "completed"},
    )
