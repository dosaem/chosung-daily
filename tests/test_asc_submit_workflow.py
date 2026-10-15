"""`asc-submit.yml` 의 Python 스텝을 실제로 돌려 본다 (티켓 35, 수정 라운드 1).

기존 테스트(`tests/test_store_metadata.py`)는 워크플로 **글자**만 봤다 — "경로가
적혀 있다", "secret 이름이 있다". 그래서 최종 리뷰가 찾은 세 결함(D-35-2 개인정보
라벨 부분 삭제, D-35-3 엉뚱한 버전 선택, D-35-7 수동 심사 노트 덮어쓰기)은
하나도 걸리지 않았다. 실패 경로는 **돌려 봐야** 보인다.

그래서 YAML 의 heredoc 에서 그 Python 블록을 그대로 꺼내 `exec` 한다. 복사본을
두지 않는 이유: 복사본은 워크플로가 바뀌면 조용히 낡는다. 바깥으로 나가는 것은
`urllib.request.urlopen` 하나뿐이라 그 자리만 메모리 대역(`FakeAsc`)으로 막으면
실제 ASC·iris 호출 없이 전체 흐름이 돈다. JWT 서명은 테스트가 그 자리에서 만든
EC 키로 진짜 `openssl` 을 쓴다(네트워크·계정 없음).
"""

import io
import json
import re
import subprocess
import textwrap
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "asc-submit.yml"
FASTLANE = REPO_ROOT / "mobile" / "ios" / "fastlane"

APP_ID = "APP1"
HEREDOC = re.compile(r"python3 - <<'PYEOF'\n(.*?)\n[ \t]*PYEOF\n", re.DOTALL)


def _step_source() -> str:
    """워크플로의 `python3 - <<'PYEOF'` 블록. 들여쓰기만 벗긴다."""
    match = HEREDOC.search(WORKFLOW.read_text(encoding="utf-8"))
    assert match, "asc-submit.yml 의 Python 스텝을 못 찾았다 — heredoc 모양이 바뀌었나"
    return textwrap.dedent(match.group(1))


def _api_key_json(tmp_path: Path) -> str:
    """진짜 EC P-256 키. 스텝이 `openssl dgst -sign` 으로 JWT 를 만든다."""
    pem = tmp_path / "ec.pem"
    subprocess.run(
        ["openssl", "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", str(pem)],
        check=True,
        capture_output=True,
    )
    return json.dumps(
        {"key_id": "TESTKEYID", "issuer_id": "TESTISSUER", "key": pem.read_text()}
    )


class _Response:
    def __init__(self, payload):
        self._raw = b"" if payload is None else json.dumps(payload).encode()

    def read(self):
        return self._raw


def _http_error(url, code):
    return urllib.error.HTTPError(url, code, "fake", {}, io.BytesIO(b'{"errors":[]}'))


class FakeAsc:
    """App Store Connect + iris 대역.

    상태는 메모리에만 있고, 어떤 호출이 어떤 순서로 왔는지(`self.calls`)와 쓰기가
    남긴 값(`self.review_detail`, `self.data_usages`, `self.attached_build`,
    `self.submitted`)을 테스트가 들여다본다.
    """

    def __init__(  # noqa: PLR0913 — 대역의 손잡이. 한 뭉치로 묶으면 호출부가 안 읽힌다
        self,
        *,
        versions,
        review_notes="",
        data_usages=("existing-usage-1",),
        iris_auth_fails=False,
        iris_write_fails=False,
        builds=("42",),
    ):
        self.versions = [dict(v) for v in versions]
        self.review_detail = {"id": "RD1", "attributes": {"notes": review_notes}}
        self.data_usages = list(data_usages)
        self.iris_auth_fails = iris_auth_fails
        self.iris_write_fails = iris_write_fails
        self.builds = list(builds)
        self.calls = []
        self.attached_build = None
        self.submitted = False
        self.published_privacy = False

    # --- urlopen 대역 -----------------------------------------------------

    def urlopen(self, request):
        method = request.method
        url = request.full_url
        body = json.loads(request.data.decode()) if request.data else None
        self.calls.append((method, url))

        if "/iris" in url:
            return _Response(self._iris(method, url.split("/iris", 1)[1], body))
        return _Response(self._api(method, url.split("appstoreconnect.apple.com", 1)[1], body))

    # --- 라우팅 -----------------------------------------------------------

    def _api(self, method, path, body):  # noqa: PLR0911, PLR0912 — 라우팅 표다
        route, _, query = path.partition("?")
        params = urllib.parse.parse_qs(query)

        if method == "GET" and route == "/v1/apps":
            return {"data": [{"id": APP_ID}]}
        if method == "PATCH" and route == f"/v1/apps/{APP_ID}":
            return {}
        if method == "GET" and route == f"/v1/apps/{APP_ID}/appStoreVersions":
            return {"data": self._versions(params)}
        if method == "GET" and route == f"/v1/apps/{APP_ID}/appPricePoints":
            return {"data": [{"id": "PT-FREE", "attributes": {"customerPrice": "0.0"}}]}
        if method == "POST" and route == "/v1/appPriceSchedules":
            return {}
        if method == "GET" and route == f"/v1/apps/{APP_ID}/appInfos":
            return {"data": [{"id": "INFO1"}]}
        if method == "GET" and route == "/v1/appInfos/INFO1/ageRatingDeclaration":
            return {"data": {"id": "AR1"}}
        if method == "PATCH" and route == "/v1/ageRatingDeclarations/AR1":
            return {}
        if method == "GET" and route.endswith("/appStoreReviewDetail"):
            return {"data": self.review_detail}
        if method == "PATCH" and route.startswith("/v1/appStoreReviewDetails/"):
            self.review_detail["attributes"].update(body["data"]["attributes"])
            return {"data": self.review_detail}
        if method == "POST" and route == "/v1/appStoreReviewDetails":
            self.review_detail = {"id": "RD1", "attributes": dict(body["data"]["attributes"])}
            return {"data": self.review_detail}
        if method == "GET" and route == "/v1/builds":
            return {
                "data": [
                    {"id": f"B{number}", "attributes": {"version": number, "expired": False}}
                    for number in self.builds
                ]
            }
        if method == "PATCH" and route.endswith("/relationships/build"):
            self.attached_build = body["data"]["id"]
            return {}
        if method == "GET" and route == "/v1/reviewSubmissions":
            return {"data": []}
        if method == "POST" and route == "/v1/reviewSubmissions":
            return {"data": {"id": "SUB1"}}
        if method == "POST" and route == "/v1/reviewSubmissionItems":
            return {}
        if method == "PATCH" and route.startswith("/v1/reviewSubmissions/"):
            self.submitted = True
            return {}
        raise AssertionError(f"대역에 없는 호출: {method} {path}")

    def _versions(self, params):
        rows = self.versions
        wanted = params.get("filter[versionString]")
        if wanted:
            rows = [v for v in rows if v["attributes"]["versionString"] in wanted[0].split(",")]
        states = params.get("filter[appStoreState]")
        if states:
            allowed = set(states[0].split(","))
            rows = [v for v in rows if v["attributes"]["appStoreState"] in allowed]
        limit = int(params.get("limit", ["200"])[0])
        return rows[:limit]

    def _iris(self, method, path, body):
        route = path.partition("?")[0]
        if method == "GET" and route == f"/v1/apps/{APP_ID}/dataUsages":
            if self.iris_auth_fails:
                raise _http_error(path, 401)
            return {"data": [{"id": usage} for usage in self.data_usages]}
        if method == "DELETE" and route.startswith("/v1/appDataUsages/"):
            self.data_usages.remove(route.rsplit("/", 1)[1])
            return {}
        if method == "POST" and route == "/v1/appDataUsages":
            if self.iris_write_fails:
                raise _http_error(path, 403)
            self.data_usages.append(f"new-{len(self.data_usages)}")
            return {}
        if method == "GET" and route == f"/v1/apps/{APP_ID}/dataUsagePublishState":
            return {"data": {"id": "PS1"}}
        if method == "PATCH" and route.startswith("/v1/appDataUsagesPublishState/"):
            self.published_privacy = True
            return {}
        raise AssertionError(f"iris 대역에 없는 호출: {method} {path}")


def _workspace(tmp_path: Path) -> Path:
    """스텝이 읽는 파일만 담은 작업 폴더(`working-directory: mobile/ios`)."""
    workspace = tmp_path / "mobile" / "ios"
    (workspace / "fastlane").mkdir(parents=True)
    (workspace / "fastlane" / "api_key.json").write_text(_api_key_json(tmp_path))
    for relative in _read_paths():
        target = workspace / "fastlane" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((FASTLANE / relative).read_text(encoding="utf-8"), encoding="utf-8")
    return workspace


def _read_paths() -> list[str]:
    """스텝이 `open(...)` 하는 레포 파일들. 워크플로 본문에서 찾아 쓴다 —
    목록을 테스트에 적어 두면 워크플로가 다른 파일을 읽기 시작할 때 낡는다."""
    found = re.findall(r"open\('fastlane/([^']+)'\)", _step_source())
    return [path for path in found if path != "api_key.json"]


def run_submit_step(fake: FakeAsc, tmp_path: Path, monkeypatch, **env) -> int:
    """스텝을 돌리고 종료 코드를 돌려준다. 0 = 끝까지, 그 밖은 실패."""
    workspace = _workspace(tmp_path)
    monkeypatch.chdir(workspace)
    monkeypatch.setattr(urllib.request, "urlopen", fake.urlopen)
    for name in (
        "BUILD_NUMBER",
        "DRY_RUN",
        "APP_VERSION",
        "REVIEW_CONTACT_FIRST_NAME",
        "REVIEW_CONTACT_LAST_NAME",
        "REVIEW_CONTACT_PHONE",
        "REVIEW_CONTACT_EMAIL",
    ):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    namespace = {"__name__": "__main__"}
    try:
        exec(compile(_step_source(), "asc-submit.yml", "exec"), namespace)
    except SystemExit as exit_code:
        return exit_code.code or 0
    return 0


def _version(version_string, state, identifier):
    return {
        "id": identifier,
        "attributes": {"versionString": version_string, "appStoreState": state},
    }


# --- D-35-3 입력한 버전에 붙인다 -------------------------------------------


def test_the_step_works_on_the_version_the_dispatch_asked_for(tmp_path, monkeypatch, capsys):
    """D-35-3 재현: 반려된 구버전이 목록 앞에 있어도 입력한 버전을 고른다.

    `app_version` 은 앞선 deliver 스텝이 메타데이터를 올린 버전이다 — 심사 노트·
    빌드 첨부·제출이 다른 버전으로 가면 올린 것과 제출한 것이 갈린다.
    """
    fake = FakeAsc(
        versions=[
            _version("0.9.0", "REJECTED", "V-OLD"),
            _version("1.0.0", "PREPARE_FOR_SUBMISSION", "V-NEW"),
        ]
    )

    exit_code = run_submit_step(fake, tmp_path, monkeypatch, APP_VERSION="1.0.0", DRY_RUN="true")

    assert exit_code == 0
    assert "V-NEW" in capsys.readouterr().out
    assert all("V-OLD" not in url for _, url in fake.calls), "구버전을 건드렸다"


def test_the_step_stops_when_the_asked_version_does_not_exist(tmp_path, monkeypatch):
    """없는 버전이면 **엉뚱한 버전을 고르지 않고** 멈춘다."""
    fake = FakeAsc(versions=[_version("0.9.0", "REJECTED", "V-OLD")])

    with pytest.raises(AssertionError, match=r"1\.0\.0"):
        run_submit_step(fake, tmp_path, monkeypatch, APP_VERSION="1.0.0", DRY_RUN="true")

    assert fake.attached_build is None
    assert fake.submitted is False


def test_the_whole_step_still_submits_the_asked_version(tmp_path, monkeypatch, capsys):
    """고친 선택·보존 규칙이 정상 경로를 막지 않는지 — 끝까지 돌려 본다."""
    fake = FakeAsc(
        versions=[
            _version("0.9.0", "REJECTED", "V-OLD"),
            _version("1.0.0", "PREPARE_FOR_SUBMISSION", "V-NEW"),
        ],
        builds=("41", "42"),
    )

    exit_code = run_submit_step(
        fake, tmp_path, monkeypatch, APP_VERSION="1.0.0", DRY_RUN="false", BUILD_NUMBER="42"
    )

    assert exit_code == 0
    assert fake.attached_build == "B42"
    assert fake.submitted is True
    assert "SUBMITTED FOR REVIEW" in capsys.readouterr().out


# --- D-35-2 개인정보 라벨 ---------------------------------------------------


def test_privacy_labels_are_left_alone_when_iris_rejects_the_team_key(
    tmp_path, monkeypatch, capsys
):
    """iris 가 401 이면 **아무것도 지우지 않고** 건너뛴다(사람이 콘솔에서 넣는다)."""
    fake = FakeAsc(
        versions=[_version("1.0.0", "PREPARE_FOR_SUBMISSION", "V1")],
        data_usages=("existing-1", "existing-2"),
        iris_auth_fails=True,
    )

    exit_code = run_submit_step(fake, tmp_path, monkeypatch, APP_VERSION="1.0.0", DRY_RUN="true")

    assert exit_code == 0
    assert fake.data_usages == ["existing-1", "existing-2"], "건너뛴다면서 지웠다"
    assert "SKIPPED" in capsys.readouterr().out
    assert not any(method == "DELETE" for method, _ in fake.calls)


def test_a_write_failure_after_the_delete_fails_the_step_instead_of_submitting(
    tmp_path, monkeypatch, capsys
):
    """D-35-2 재현: 삭제는 됐는데 쓰기가 실패하면 **부분 신고 상태**다.

    되돌릴 수 없으므로(지운 라벨의 id 는 돌아오지 않는다) 조용히 넘어가지 않고
    스텝을 실패시킨다 — 그래야 빌드 첨부·심사 제출까지 가지 않는다.
    """
    fake = FakeAsc(
        versions=[_version("1.0.0", "PREPARE_FOR_SUBMISSION", "V1")],
        data_usages=("existing-1",),
        iris_write_fails=True,
    )

    with pytest.raises(urllib.error.HTTPError):
        run_submit_step(fake, tmp_path, monkeypatch, APP_VERSION="1.0.0", DRY_RUN="false")

    assert fake.submitted is False, "부분 라벨 상태로 심사에 제출했다"
    assert fake.attached_build is None
    assert "SKIPPED" not in capsys.readouterr().out, "실제 상태와 반대인 로그"


def test_privacy_labels_are_published_when_iris_works(tmp_path, monkeypatch, capsys):
    fake = FakeAsc(
        versions=[_version("1.0.0", "PREPARE_FOR_SUBMISSION", "V1")],
        data_usages=("existing-1",),
    )

    exit_code = run_submit_step(fake, tmp_path, monkeypatch, APP_VERSION="1.0.0", DRY_RUN="true")

    assert exit_code == 0
    assert fake.published_privacy is True
    assert "existing-1" not in fake.data_usages
    assert "PUBLISHED" in capsys.readouterr().out


# --- D-35-7 수동 심사 노트 --------------------------------------------------


def test_the_step_does_not_overwrite_review_notes_a_human_filled_in(
    tmp_path, monkeypatch, capsys
):
    """D-35-7 재현: 콘솔의 Sandbox 계정이 들어간 노트를 레포 플레이스홀더로 덮지 않는다.

    권장 순서는 dry run → 콘솔에 Sandbox 정보 입력 → 실제 제출이다. 마지막 실행이
    노트를 다시 쓰면 심사자가 쓸 계정이 사라진다.
    """
    filled = "Sandbox tester: real.tester@example.com / correct horse battery"
    fake = FakeAsc(
        versions=[_version("1.0.0", "PREPARE_FOR_SUBMISSION", "V1")],
        review_notes=filled,
    )

    exit_code = run_submit_step(fake, tmp_path, monkeypatch, APP_VERSION="1.0.0", DRY_RUN="true")

    assert exit_code == 0
    assert fake.review_detail["attributes"]["notes"] == filled
    assert "<SANDBOX_TESTER_EMAIL>" not in fake.review_detail["attributes"]["notes"]
    assert "ASC 콘솔" in capsys.readouterr().out


@pytest.mark.parametrize("existing", ["", "   ", "Sandbox tester: <SANDBOX_TESTER_EMAIL>"])
def test_the_step_fills_empty_or_placeholder_review_notes_from_the_repo(
    existing, tmp_path, monkeypatch
):
    """반대 방향 — 콘솔이 비었거나 아직 플레이스홀더면 레포 노트를 올린다."""
    fake = FakeAsc(
        versions=[_version("1.0.0", "PREPARE_FOR_SUBMISSION", "V1")],
        review_notes=existing,
    )

    exit_code = run_submit_step(fake, tmp_path, monkeypatch, APP_VERSION="1.0.0", DRY_RUN="true")

    assert exit_code == 0
    notes = fake.review_detail["attributes"]["notes"]
    assert "ACCOUNT DELETION PATH" in notes
    assert "<SANDBOX_TESTER_EMAIL>" in notes


def test_fastlane_deliver_cannot_touch_the_review_notes(tmp_path, monkeypatch):
    """`deliver` 는 `review_information/` 의 **정해진 파일 이름만** 읽는다.

    `notes.txt` 가 그 폴더에 있으면 deliver 가 심사 상세를 PATCH 해서, 위의
    보존 규칙과 상관없이 콘솔 값을 덮는다(fastlane 2.232.2
    `deliver/lib/deliver/upload_metadata.rb` `REVIEW_INFORMATION_VALUES`).
    그래서 정본을 그 이름에서 뺐다 — 이 테스트가 되돌아가는 것을 막는다.
    """
    deliver_owned = {"notes", "demo_user", "demo_password", "first_name", "last_name",
                     "phone_number", "email_address", "review_notes", "review_demo_user",
                     "review_demo_password", "review_first_name", "review_last_name",
                     "review_phone_number", "review_email"}

    review_information = FASTLANE / "metadata" / "review_information"
    present = {path.name.removesuffix(".txt") for path in review_information.glob("*.txt")}

    assert not (present & deliver_owned), f"deliver 가 덮어쓰는 이름: {present & deliver_owned}"
    assert [path for path in review_information.glob("notes*")], "심사 노트 정본이 없다"
