"""ASC 보조 워크플로 4개 — `asc-status` · `asc-build-compliance` · `asc-diagnose` ·
`testflight-tester` (티켓 41).

구조 검사는 네 개 다 본다(트리거·러너·번들 ID·키를 파일로 안 떨어뜨림·개인 주소
없음). 그 위에 `asc-build-compliance.yml` 의 Python 스텝은 **실제로 돌려** 본다 —
유일하게 ASC 쪽에 쓰기(`PATCH /v1/builds/{id}`)를 하는 워크플로라서, "값이 이미
있는 빌드를 건드리지 않는다" 와 "만료된 빌드는 건너뛴다" 는 글자만 봐서는 못
지킨다. 바깥으로 나가는 것은 `urllib.request.urlopen` 하나뿐이고, JWT 서명은
테스트가 그 자리에서 만든 EC 키로 진짜 `openssl` 을 쓴다(네트워크·계정 없음).
`tests/test_asc_submit_workflow.py` 와 같은 방식이다.
"""

import ast
import io
import json
import re
import subprocess
import tempfile
import textwrap
import urllib.error
import urllib.request
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"

HELPERS = (
    "asc-status.yml",
    "asc-build-compliance.yml",
    "asc-diagnose.yml",
    "testflight-tester.yml",
)
WITH_EMAIL = ("asc-diagnose.yml", "testflight-tester.yml")
# `token()` 의 P8 임시 파일을 쓰는 워크플로 전부. `asc-submit.yml` 은 보조가 아니지만
# **같은 `token()`** 이라 같은 계약을 진다(D-41-1).
SIGNING_WORKFLOWS = (*HELPERS, "asc-submit.yml")

HEREDOC = re.compile(r"python3 - <<'PYEOF'\n(.*?)\n[ \t]*PYEOF\n", re.DOTALL)
APP_ID = "APP1"


def _text(name: str) -> str:
    return (WORKFLOW_DIR / name).read_text(encoding="utf-8")


def _step_source(name: str) -> str:
    match = HEREDOC.search(_text(name))
    assert match, f"{name} 의 Python 스텝을 못 찾았다 — heredoc 모양이 바뀌었나"
    return textwrap.dedent(match.group(1))


def _triggers(name: str) -> dict:
    doc = yaml.safe_load(_text(name))
    # `on:` 은 YAML 1.1 에서 불리언 True 로 읽힌다.
    return doc[True] if True in doc else doc["on"]


# --- 구조 (네 개 공통) --------------------------------------------------------


@pytest.mark.parametrize("name", HELPERS)
def test_every_helper_is_dispatch_only(name: str):
    """사람이 부를 때만 돈다. 푸시로도 돌면 ASC 쪽에 쓰기가 자동으로 나간다."""
    triggers = _triggers(name)

    assert set(triggers) == {"workflow_dispatch"}, triggers


@pytest.mark.parametrize("name", HELPERS)
def test_every_helper_runs_on_the_self_hosted_runner(name: str):
    """ASC API 키를 쓰는 잡은 사용자 맥에서만 돈다(`flutter.yml` 과 같은 선택)."""
    doc = yaml.safe_load(_text(name))
    jobs = doc["jobs"]

    assert len(jobs) == 1, jobs
    assert next(iter(jobs.values()))["runs-on"] == "self-hosted"


@pytest.mark.parametrize("name", HELPERS)
def test_every_helper_targets_this_apps_bundle_id(name: str):
    """BASELINE 복사본이라 번들 ID 치환을 빠뜨리면 **남의 앱**을 고친다."""
    source = _step_source(name)

    assert "com.dosaem.chosung" in source
    assert "buildurpalace" not in source.lower()


@pytest.mark.parametrize("name", HELPERS)
def test_every_helper_stops_when_the_api_key_secret_is_empty(name: str):
    """secret 이 비면 `json.loads('')` 가 뜻 모를 예외로 죽는다 — 먼저 멈춘다."""
    source = _step_source(name)

    assert "APP_STORE_CONNECT_API_KEY secret 이 없다" in source


@pytest.mark.parametrize("name", HELPERS)
def test_no_helper_writes_the_api_key_to_disk(name: str):
    """self-hosted 러너는 잡이 끝나도 사용자 맥이 남는다. fastlane 을 안 쓰므로
    fastlane 용 `api_key.json` 을 만들 이유가 없다.

    JWT 서명용 P8 임시 파일은 다른 얘기다 — `openssl` 이 파일 경로만 받아서 어쩔 수
    없이 생기고, 아래 두 테스트가 그게 **반드시 지워지는지**를 본다(D-41-1).

    보는 것은 **실행되는 코드**(heredoc 안의 Python)다. 머리말 주석은 "fastlane 용
    `api_key.json` 은 만들지 않는다" 처럼 그 파일을 말로 언급해야 하고, 말은 파일을
    만들지 않는다.
    """
    source = _step_source(name)

    assert "api_key.json" not in source
    assert "API_KEY_JSON" in _text(name)


@pytest.mark.parametrize("name", SIGNING_WORKFLOWS)
def test_the_temp_signing_key_is_removed_in_a_finally(name: str):
    """D-41-1: `os.unlink(kp)` 가 `try/finally` 의 finally 에 있어야 한다.

    정상 경로의 `unlink` 한 줄로는 모자란다 — `openssl` 이 없거나 죽으면
    `subprocess.run` 이 던지고 그 줄에 닿지 못해 `/tmp/*.p8` 가 self-hosted 맥에
    남는다. 글자가 아니라 구문을 본다: 워크플로마다 들여쓰기·줄바꿈이 조금씩
    달라져도 같은 계약을 지키는지 알 수 있다.
    """
    tree = ast.parse(_step_source(name), name)
    func = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "token"
    )

    unlinks_in_finally = [
        call
        for try_node in (n for n in ast.walk(func) if isinstance(n, ast.Try))
        for statement in try_node.finalbody
        for call in ast.walk(statement)
        if isinstance(call, ast.Call) and ast.unparse(call.func) == "os.unlink"
    ]

    assert unlinks_in_finally, f"{name} 의 token() 이 임시 P8 를 finally 에서 안 지운다"


@pytest.mark.parametrize("name", HELPERS)
def test_no_helper_carries_a_personal_email(name: str):
    """BASELINE 은 운영자 주소를 워크플로 기본값에 박아 뒀다 — 레포에 안 남긴다."""
    text = _text(name)

    assert "@gmail.com" not in text
    assert "@dosaem.com" not in text


@pytest.mark.parametrize("name", WITH_EMAIL)
def test_the_email_falls_back_to_the_repo_variable(name: str):
    """입력을 비우고 돌릴 수 있어야 한다 — 그 기본값이 variable 이다."""
    text = _text(name)
    source = _step_source(name)

    assert "github.event.inputs.email || vars.TESTFLIGHT_TESTER_EMAIL" in text
    assert "TESTFLIGHT_TESTER_EMAIL 을 채운다" in source


@pytest.mark.parametrize("name", HELPERS)
def test_every_helper_step_compiles(name: str):
    """heredoc 안의 Python 은 러너에서 처음 실행된다 — 문법 오류를 여기서 잡는다."""
    compile(_step_source(name), name, "exec")


# --- asc-build-compliance: 실제로 돌려 본다 ----------------------------------


class _Response:
    def __init__(self, payload):
        self._raw = b"" if payload is None else json.dumps(payload).encode()

    def read(self):
        return self._raw


class FakeAsc:
    """App Store Connect 대역. 어떤 호출이 어떤 순서로 왔는지 `calls` 에 쌓는다."""

    def __init__(self, builds, apps=None):
        self.builds = builds
        self.apps = apps if apps is not None else [{"id": APP_ID}]
        self.calls: list[tuple[str, str]] = []
        self.patched: list[tuple[str, object]] = []

    def urlopen(self, req, *args, **kwargs):
        method, url = req.get_method(), req.full_url
        self.calls.append((method, url))

        if "/v1/apps?" in url:
            return _Response({"data": self.apps})
        if "/v1/builds?" in url:
            return _Response({"data": self.builds})
        if method == "PATCH" and "/v1/builds/" in url:
            body = json.loads(req.data.decode())
            self.patched.append(
                (url.rsplit("/", 1)[1], body["data"]["attributes"]["usesNonExemptEncryption"])
            )
            return _Response({"data": body["data"]})

        raise urllib.error.HTTPError(url, 404, "unexpected", {}, io.BytesIO(b'{"errors":[]}'))


def _api_key_json(tmp_path: Path) -> str:
    """진짜 EC P-256 키. 스텝이 `openssl dgst -sign` 으로 JWT 를 만든다."""
    pem = tmp_path / "ec.pem"
    subprocess.run(
        ["openssl", "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", str(pem)],
        check=True,
        capture_output=True,
    )
    return json.dumps({"key_id": "TESTKEYID", "issuer_id": "TESTISSUER", "key": pem.read_text()})


def _build(version, *, non_exempt=None, expired=False, identifier=None, state="VALID"):
    return {
        "id": identifier or f"B-{version}",
        "attributes": {
            "version": version,
            "processingState": state,
            "usesNonExemptEncryption": non_exempt,
            "expired": expired,
        },
    }


def run_compliance_step(fake: FakeAsc, tmp_path: Path, monkeypatch, **env) -> int:
    monkeypatch.setattr(urllib.request, "urlopen", fake.urlopen)
    monkeypatch.setenv("API_KEY_JSON", env.pop("API_KEY_JSON", _api_key_json(tmp_path)))
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    namespace = {"__name__": "__main__"}
    try:
        source = _step_source("asc-build-compliance.yml")
        exec(compile(source, "asc-build-compliance.yml", "exec"), namespace)
    except SystemExit as exit_code:
        return exit_code.code or 0
    return 0


def test_compliance_fills_only_the_builds_that_have_no_answer(tmp_path, monkeypatch, capsys):
    fake = FakeAsc(builds=[_build("3"), _build("2")])

    exit_code = run_compliance_step(fake, tmp_path, monkeypatch)

    assert exit_code == 0
    assert fake.patched == [("B-3", False), ("B-2", False)]
    assert "patched 2 build(s)" in capsys.readouterr().out


def test_compliance_does_not_overwrite_an_answer_a_human_already_gave(tmp_path, monkeypatch):
    """콘솔에서 `true` 로 답한 빌드를 여기서 `false` 로 뒤집으면 **거짓 신고**다."""
    fake = FakeAsc(builds=[_build("3", non_exempt=True), _build("2", non_exempt=False)])

    exit_code = run_compliance_step(fake, tmp_path, monkeypatch)

    assert exit_code == 0
    assert fake.patched == []


def test_compliance_skips_expired_builds(tmp_path, monkeypatch):
    """만료된 빌드는 제출에 못 쓴다 — PATCH 가 의미 없다."""
    fake = FakeAsc(builds=[_build("1", expired=True), _build("3")])

    run_compliance_step(fake, tmp_path, monkeypatch)

    assert fake.patched == [("B-3", False)]


def test_compliance_stops_when_the_app_is_not_in_asc_yet(tmp_path, monkeypatch, capsys):
    """D2 전에는 앱이 없다 — `data[0]` 으로 IndexError 를 내지 않고 할 일을 찍는다."""
    fake = FakeAsc(builds=[], apps=[])

    exit_code = run_compliance_step(fake, tmp_path, monkeypatch)

    assert exit_code == 1
    assert "앱이 없다" in capsys.readouterr().out
    assert fake.patched == []


def test_compliance_does_nothing_when_no_build_was_uploaded(tmp_path, monkeypatch, capsys):
    fake = FakeAsc(builds=[])

    exit_code = run_compliance_step(fake, tmp_path, monkeypatch)

    assert exit_code == 0
    assert "할 일 없음" in capsys.readouterr().out
    assert fake.patched == []


def test_compliance_stops_when_the_secret_is_empty(tmp_path, monkeypatch, capsys):
    fake = FakeAsc(builds=[_build("3")])

    exit_code = run_compliance_step(fake, tmp_path, monkeypatch, API_KEY_JSON="")

    assert exit_code == 1
    assert "APP_STORE_CONNECT_API_KEY" in capsys.readouterr().out
    assert fake.calls == []


# --- D-41-1: JWT 서명용 P8 임시 파일 ------------------------------------------
#
# 위 `test_the_temp_signing_key_is_removed_in_a_finally` 는 다섯 워크플로의 **구문**을
# 본다. 여기서는 `asc-build-compliance.yml` 의 `token()` 을 실제로 돌려서, 서명이
# 터져도 파일이 남지 않는 것을 디렉터리로 확인한다 — 글자도 구문도 "정말 지워졌나"
# 는 못 본다. `tempfile.tempdir` 를 `tmp_path` 로 돌려 진짜 `/tmp` 는 건드리지 않는다.


def _p8_files(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.p8"))


def test_the_temp_signing_key_is_gone_after_a_normal_run(tmp_path, monkeypatch):
    key_json = _api_key_json(tmp_path)
    signing_tmp = tmp_path / "tmp"
    signing_tmp.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(signing_tmp))
    fake = FakeAsc(builds=[_build("3")])

    exit_code = run_compliance_step(fake, tmp_path, monkeypatch, API_KEY_JSON=key_json)

    assert exit_code == 0
    assert fake.patched == [("B-3", False)]
    assert _p8_files(signing_tmp) == []


def test_the_temp_signing_key_is_gone_even_when_openssl_blows_up(tmp_path, monkeypatch):
    """D-41-1: `openssl` 이 없는(또는 죽는) 러너에서 `subprocess.run` 이 던지면
    정상 경로의 `os.unlink` 에 닿지 못한다. self-hosted 맥은 잡이 끝나도 남아서
    그 P8 가 그대로 쌓인다."""
    key_json = _api_key_json(tmp_path)
    signing_tmp = tmp_path / "tmp"
    signing_tmp.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(signing_tmp))

    # 서명(`openssl dgst -sign`)만 터뜨린다 — `run_compliance_step` 이 키를 만들 때
    # 쓰는 `openssl ecparam` 까지 막으면 `token()` 에 들어가 보지도 못한다.
    real_run = subprocess.run

    def openssl_is_missing(args, *rest, **kwargs):
        if "dgst" in args:
            raise FileNotFoundError("openssl")
        return real_run(args, *rest, **kwargs)

    monkeypatch.setattr(subprocess, "run", openssl_is_missing)
    fake = FakeAsc(builds=[_build("3")])

    with pytest.raises(FileNotFoundError):
        run_compliance_step(fake, tmp_path, monkeypatch, API_KEY_JSON=key_json)

    assert _p8_files(signing_tmp) == [], "서명이 터지자 P8 가 남았다"
    # 토큰을 못 만들었으니 ASC 로는 아무것도 나가지 않았다.
    assert fake.calls == []
