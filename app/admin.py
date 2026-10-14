"""운영자 페이지(`/admin`) — 단어 CRUD 와 CSV 업로드.

인증은 따로 만들지 않는다: 이미 있는 구글 OAuth 세션의 **연결된 이메일**이
`ADMIN_EMAILS` 에 있으면 운영자다(README "설계 판단 15."). 비밀번호·별도 로그인
화면이 없다는 게 핵심이고, 그래서 이 모듈에는 로그인 시작 경로가 없다 — 현행
OAuth 진입(`GET /api/v1/auth/<provider>/login`)이 Bearer 토큰으로 심은 세션을
전제하므로(app/api/oauth.py `sync_session`), 로그인 안 된 브라우저는 `/` 로 보내
"웹에서 구글 로그인 후 /admin" 을 안내한다.

페이지는 `app/api/*` 가 아니라 여기 있다 — JSON API 가 아니라 Jinja 페이지라서
`app/web.py` 와 같은 층이다. 다만 운영자 화면만 블루프린트를 따로 둬서
`/admin` prefix 와 가드 데코레이터가 한곳에 모이게 했다.
"""

import csv
import io
from functools import wraps

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.csrf import csrf_protected, issue_csrf_token
from app.errors import ForbiddenError, ValidationError
from app.extensions import db
from app.models import PuzzleLanguage, Word, WordCategory
from app.repositories import account_repository
from app.services import word_service

bp = Blueprint("admin", __name__, url_prefix="/admin")

LOGIN_GUIDE = (
    "운영자 페이지는 웹에서 구글 로그인을 먼저 해야 들어갈 수 있어요. "
    "로그인한 뒤에 /admin 으로 다시 들어와주세요."
)


def admin_required(view):
    """세션 → Guest → `Account.email ∈ ADMIN_EMAILS` 를 통과한 요청만 들여보낸다.

    로그인 안 된 브라우저(세션 없음 또는 계정 미연결)는 403 이 아니라 `/` 로
    보낸다 — 운영자가 `/admin` 을 북마크해 두고 들어오는 게 정상 경로이고, 그때
    필요한 건 거부가 아니라 "로그인을 먼저 하라" 는 안내다. 로그인은 됐지만
    허용 목록에 없는 이메일은 403 `FORBIDDEN`(스펙 §A' API 표).
    """

    @wraps(view)
    def wrapper(*args, **kwargs):
        guest_id = session.get("current_guest_id")
        account = account_repository.find_by_guest(guest_id) if guest_id else None
        if account is None:
            flash(LOGIN_GUIDE)
            return redirect(url_for("web.index"))

        if (account.email or "").strip().lower() not in current_app.config["ADMIN_EMAILS"]:
            raise ForbiddenError()

        g.admin_email = account.email
        return view(*args, **kwargs)

    return wrapper


@bp.get("/")
@admin_required
def words():
    """단어 목록 — 언어·카테고리·검색어 필터 + 페이지네이션."""
    filters = _read_filters()
    pagination = word_service.search_words(
        language=filters["language"],
        category=filters["category"],
        keyword=filters["keyword"],
        page=request.args.get("page", default=1, type=int),
    )
    return render_template(
        "admin/words.html",
        pagination=pagination,
        filters=filters,
        filter_query=_filter_query(filters),
        csrf_token=issue_csrf_token(),
    )


@bp.get("/words/new")
@admin_required
def new_word():
    return _render_word_form(_blank_form())


@bp.post("/words")
@admin_required
@csrf_protected
def create_word():
    form = _read_word_form()
    try:
        word = word_service.create_word(**form)
    except ValidationError as err:
        return _render_word_form(form, error=err.message)

    flash(f"'{word.answer}' 를 추가했어요.")
    return redirect(url_for("admin.words"))


@bp.get("/words/<int:word_id>/edit")
@admin_required
def edit_word(word_id):
    word = db.get_or_404(Word, word_id)
    return _render_word_form(
        {
            "language": word.language.value,
            "category": word.category.value,
            "answer": word.answer,
            "hint": word.hint,
        },
        word=word,
    )


@bp.post("/words/<int:word_id>")
@admin_required
@csrf_protected
def update_word(word_id):
    word = db.get_or_404(Word, word_id)
    form = _read_word_form()
    try:
        word_service.update_word(word, **form)
    except ValidationError as err:
        # 고치던 값을 그대로 다시 그린다 — 폼이 비면 운영자가 처음부터 다시 적는다.
        db.session.rollback()
        return _render_word_form(form, word=word, error=err.message)

    flash(f"'{word.answer}' 를 수정했어요.")
    return redirect(url_for("admin.words"))


@bp.post("/words/<int:word_id>/delete")
@admin_required
@csrf_protected
def delete_word(word_id):
    word = db.get_or_404(Word, word_id)
    # 삭제 뒤에는 인스턴스에서 값을 못 읽으니 메시지에 쓸 정답을 먼저 뽑아둔다.
    answer = word.answer
    try:
        word_service.delete_word(word)
    except ValidationError as err:
        flash(err.message)
    else:
        flash(f"'{answer}' 를 삭제했어요.")
    return redirect(url_for("admin.words"))


@bp.get("/words/import")
@admin_required
def import_form():
    return _render_import()


@bp.post("/words/import")
@admin_required
@csrf_protected
def import_csv():
    """CSV 업로드. 파일을 행 리스트로 바꾸는 것까지가 이 함수의 일이고,
    적재 규칙은 `word_service.import_word_rows` 가 들고 있다."""
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return _render_import(error=f"올릴 CSV 파일을 골라주세요 (헤더: {_csv_header()}).")

    try:
        # utf-8-sig 로 읽으면 엑셀이 붙이는 BOM 이 첫 헤더 이름에 끌려들어오지 않는다.
        text = upload.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        return _render_import(
            error="UTF-8 로 저장한 CSV 만 읽을 수 있어요 (엑셀은 'CSV UTF-8' 로 저장)."
        )

    # restkey 에 이름을 줘서 헤더보다 많은 값이 온 행을 서비스가 알아볼 수 있게 한다
    # (기본값 None 이면 초과 값이 이름 없는 키에 담겨 조용히 버려진다).
    reader = csv.DictReader(io.StringIO(text), restkey=word_service.CSV_EXTRA_FIELD_KEY)
    try:
        fieldnames = reader.fieldnames
        rows = list(reader)
    except csv.Error as err:
        # 한 칸이 파서 한도(131072자)를 넘으면 여기서 터진다. 그냥 올려보내면 500 이
        # 되고 결과 표도 못 그리니, 운영자가 고칠 수 있는 문구로 바꿔 돌려준다.
        return _render_import(error=f"CSV 를 읽지 못했어요: {err}. 한 칸에 너무 긴 값이 있어요.")

    missing = word_service.missing_csv_columns(fieldnames)
    if missing:
        return _render_import(
            error=f"헤더에 없는 열: {', '.join(missing)}. 첫 줄은 {_csv_header()} 여야 해요."
        )

    duplicated = word_service.duplicate_csv_columns(fieldnames)
    if duplicated:
        return _render_import(
            error=f"헤더에 같은 열이 두 번 있어요: {', '.join(duplicated)}. "
            f"첫 줄은 {_csv_header()} 여야 해요."
        )

    return _render_import(results=word_service.import_word_rows(rows))


def _csv_header() -> str:
    return ",".join(word_service.WORD_CSV_COLUMNS)


def _read_filters() -> dict:
    """목록 필터를 쿼리스트링에서 읽는다. 모르는 값은 필터 없음으로 둔다 —
    손으로 URL 을 고친 요청 때문에 목록이 에러 페이지가 되면 안 된다."""
    return {
        "language": _parse_enum(PuzzleLanguage, request.args.get("language")),
        "category": _parse_enum(WordCategory, request.args.get("category")),
        "keyword": (request.args.get("q") or "").strip(),
    }


def _filter_query(filters: dict) -> dict:
    """쪽 넘김 링크에 그대로 실을 필터. 비어 있는 필터는 URL 에 안 넣는다 —
    "2쪽" 을 눌렀을 때 보고 있던 필터가 풀리지 않아야 한다."""
    query = {
        "language": filters["language"].value if filters["language"] else None,
        "category": filters["category"].value if filters["category"] else None,
        "q": filters["keyword"] or None,
    }
    return {key: value for key, value in query.items() if value}


def _parse_enum(enum_cls, raw: str | None):
    try:
        return enum_cls((raw or "").strip())
    except ValueError:
        return None


def _blank_form() -> dict:
    return {
        "language": PuzzleLanguage.KO.value,
        "category": WordCategory.GENERAL.value,
        "answer": "",
        "hint": "",
    }


def _read_word_form() -> dict:
    """폼 입력 네 개를 그대로 읽는다. 검증은 서비스(`parse_word_input`)가 한다 —
    실패 사유 문구가 폼과 CSV 두 군데에 따로 생기지 않게."""
    return {
        "language": request.form.get("language") or "",
        "category": request.form.get("category") or "",
        "answer": request.form.get("answer") or "",
        "hint": request.form.get("hint") or "",
    }


def _render_word_form(form: dict, word: Word | None = None, error: str | None = None):
    return render_template(
        "admin/word_form.html",
        form=form,
        word=word,
        error=error,
        languages=list(PuzzleLanguage),
        categories=list(WordCategory),
        csrf_token=issue_csrf_token(),
    )


def _render_import(results=None, error: str | None = None):
    return render_template(
        "admin/import.html",
        results=results,
        error=error,
        csv_header=_csv_header(),
        row_status=word_service.RowStatus,
        csrf_token=issue_csrf_token(),
    )


def register_admin(app):
    app.register_blueprint(bp)
