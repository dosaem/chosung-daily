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
from datetime import date, datetime, timedelta
from functools import wraps

import requests
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

from app.access_log import mask_email, remember_actor
from app.config import KST
from app.csrf import csrf_protected, issue_csrf_token
from app.errors import ForbiddenError, NotFoundError, ValidationError
from app.extensions import db
from app.models import PuzzleLanguage, Word, WordCategory
from app.repositories import account_repository
from app.schemas.book import BookSearchResult
from app.services import (
    app_config_service,
    puzzle_schedule_service,
    task_dispatch,
    word_candidate_service,
    word_generation_service,
    word_service,
)
from app.services.book_lookup_service import search_google_books
from app.services.puzzle_schedule_service import SCHEDULE_DAYS
from app.services.word_pool_service import (
    LOW_WORD_POOL_THRESHOLD_DAYS,
    remaining_days_by_language,
)
from app.utils.time import utcnow

bp = Blueprint("admin", __name__, url_prefix="/admin")

# 배정표의 날짜 옆에 붙이는 요일. 일요일은 책 제목 라운드라(배정 규칙 05) 운영자가
# 요일을 보고 그 날짜의 단어를 고른다.
WEEKDAY_NAMES = ("월", "화", "수", "목", "금", "토", "일")

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

        # 허용 목록 판정 **전에** 적는다 — 거부된 접근 시도도 접속기록에
        # 남아야 하고(고시 제8조), 그때 누가 시도했는지가 점검의 핵심이다.
        remember_actor(mask_email(account.email) if account.email else f"guest.{account.guest_id}")

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


# --- LLM 단어 후보 검수 ------------------------------------------------------


@bp.get("/candidates")
@admin_required
def candidates():
    """LLM 이 만든 후보 목록(승인 대기만). 운영자가 힌트를 고쳐 승인하거나 거절한다.

    LLM 결과가 `word` 로 바로 들어가지 않는 이유는 `WordCandidate` 모델 주석에
    있다. 여기서 "후보 생성" 은 Celery 태스크를 큐에 넣기만 하고 돌아온다 —
    LLM 호출은 수십 초라 요청 안에서 기다리지 않는다.
    """
    language = _parse_enum(PuzzleLanguage, request.args.get("language"))
    return render_template(
        "admin/candidates.html",
        language=language,
        languages=list(PuzzleLanguage),
        pending=word_candidate_service.list_pending(language),
        pending_counts=word_candidate_service.pending_counts(),
        recent=word_candidate_service.recent_reviewed(),
        review_enabled=current_app.config["LLM_REVIEW_ENABLED"],
        generation_enabled=current_app.config["LLM_WORD_GENERATION_ENABLED"],
        model=current_app.config["LLM_MODEL"],
        monthly_cost=word_generation_service.monthly_cost_usd(utcnow()),
        monthly_budget=current_app.config["LLM_MONTHLY_BUDGET_USD"],
        max_pending=current_app.config["LLM_MAX_PENDING_CANDIDATES"],
        csrf_token=issue_csrf_token(),
    )


@bp.post("/candidates/review")
@admin_required
@csrf_protected
def review_candidates():
    ids = request.form.getlist("candidate_id", type=int)
    language = request.form.get("language") or None
    if not ids:
        flash("승인하거나 거절할 후보를 골라주세요.")
        return redirect(url_for("admin.candidates", language=language))

    if request.form.get("action") == "reject":
        result = word_candidate_service.reject(ids, (request.form.get("reason") or "").strip())
        flash(f"후보 {len(result.rejected)}개를 거절했어요.")
    else:
        hints = {
            cid: (request.form.get(f"hint-{cid}") or "").strip()
            for cid in ids
            if (request.form.get(f"hint-{cid}") or "").strip()
        }
        result = word_candidate_service.approve(ids, hints)
        flash(f"후보 {len(result.approved)}개를 단어로 추가했어요.")
        for candidate, reason in result.failed:
            flash(f"'{candidate.answer}' 는 추가하지 못해 거절로 돌렸어요: {reason}")
    return redirect(url_for("admin.candidates", language=language))


@bp.post("/candidates/generate")
@admin_required
@csrf_protected
def generate_candidates():
    language = _read_language(request.form)
    if not current_app.config["LLM_WORD_GENERATION_ENABLED"]:
        flash("LLM 후보 생성이 꺼져 있어요 (LLM_WORD_GENERATION_ENABLED).")
    else:
        task_dispatch.enqueue_task(word_generation_service.TASK_NAME, language.value, "admin")
        flash(
            f"{language.value} 후보 생성을 요청했어요. 끝나면 Slack 으로 알리고, "
            "이 화면을 새로고침하면 보여요."
        )
    return redirect(url_for("admin.candidates", language=language.value))


@bp.post("/candidates/review-llm")
@admin_required
@csrf_protected
def review_candidates_llm():
    """승인 대기 전부를 배치 단위로 LLM 심사관에게 보낸다(심사가 꺼져 있으면 안내만)."""
    if not current_app.config["LLM_REVIEW_ENABLED"]:
        flash("LLM 심사가 꺼져 있어요 (LLM_REVIEW_ENABLED).")
        return redirect(url_for("admin.candidates"))
    batch_ids = word_candidate_service.pending_batch_ids()
    for batch_id in batch_ids:
        task_dispatch.enqueue_task(word_generation_service.REVIEW_TASK_NAME, batch_id)
    flash(f"배치 {len(batch_ids)}개를 LLM 심사에 보냈어요. 끝나면 Slack 으로 알려요.")
    return redirect(url_for("admin.candidates"))


# --- 배정표·잔량 ---------------------------------------------------------


@bp.get("/schedule")
@admin_required
def schedule():
    """언어별 다음 30일 배정표 + 언어별 잔량 카드.

    조회는 쓰기를 하지 않는다 — 빈 날짜를 여기서 배정해버리면 운영자가 화면을
    열어보는 것만으로 단어 풀이 줄어든다. 배정은 자정 Beat 와 아래 교체 폼만 한다.
    """
    language = _read_language(request.args)
    return render_template(
        "admin/schedule.html",
        language=language,
        languages=list(PuzzleLanguage),
        days=puzzle_schedule_service.upcoming_schedule(language),
        stock=remaining_days_by_language(),
        low_threshold=LOW_WORD_POOL_THRESHOLD_DAYS,
        weekday_names=WEEKDAY_NAMES,
    )


@bp.get("/schedule/<puzzle_date>/replace")
@admin_required
def replace_form(puzzle_date):
    """교체할 단어를 고르는 화면. 단어 찾기는 목록 검색(`search_words`)을 그대로 쓴다.

    배정표 30행에 전체 단어 select 를 그리지 않는 이유: 단어 풀은 수천 개 규모라
    (`word_pool_service`) 한 화면에 30벌을 그리면 HTML 이 메가바이트가 되고,
    운영자는 어차피 "기념일에 맞는 그 단어" 를 검색해서 찾는다(US 54).
    """
    target_date, language = _read_schedule_target(puzzle_date)
    keyword = (request.args.get("q") or "").strip()
    pagination = word_service.search_words(
        language=language,
        keyword=keyword,
        page=request.args.get("page", default=1, type=int),
    )
    # 배정표를 한 번 읽어 두 가지를 같이 뽑는다: 지금 그 날짜의 단어와, 이번 창에
    # 이미 배정된 단어 id 들("이미 배정됨" 표시 — 같은 단어가 30일 안에 두 번
    # 나오는 걸 운영자가 모르고 고르지 않게).
    schedule_days = puzzle_schedule_service.upcoming_schedule(language)
    return render_template(
        "admin/schedule_replace.html",
        puzzle_date=target_date,
        language=language,
        keyword=keyword,
        pagination=pagination,
        current_word=next(
            (day.word for day in schedule_days if day.puzzle_date == target_date), None
        ),
        assigned_word_ids={day.word.id for day in schedule_days if day.word is not None},
        csrf_token=issue_csrf_token(),
    )


@bp.post("/schedule/<puzzle_date>/replace")
@admin_required
@csrf_protected
def replace_word(puzzle_date):
    target_date, language = _read_schedule_target(puzzle_date)
    try:
        puzzle = puzzle_schedule_service.replace_assignment(
            target_date, language, request.form.get("word_id", type=int) or 0
        )
    except ValidationError as err:
        flash(err.message)
        return redirect(
            url_for(
                "admin.replace_form",
                puzzle_date=target_date.isoformat(),
                language=language.value,
            )
        )

    flash(
        f"{target_date.isoformat()} ({language.value}) 퍼즐을 '{puzzle.word.answer}' 로 바꿨어요."
    )
    return redirect(url_for("admin.schedule", language=language.value))


# --- 점검 모드·최소 앱 버전 ---------------------------------------------


@bp.get("/settings")
@admin_required
def settings_form():
    current = app_config_service.get_operator_settings()
    return _render_settings(
        {
            "maintenance_enabled": current.maintenance_enabled,
            "maintenance_message": current.maintenance_message,
            "min_app_version_ios": current.min_app_version_ios,
            "min_app_version_android": current.min_app_version_android,
        }
    )


@bp.post("/settings")
@admin_required
@csrf_protected
def save_settings():
    form = {
        # 체크박스는 꺼져 있으면 폼에 아예 안 실린다 — 키가 없으면 꺼짐이다.
        "maintenance_enabled": request.form.get("maintenance_enabled") == "on",
        "maintenance_message": request.form.get("maintenance_message") or "",
        "min_app_version_ios": request.form.get("min_app_version_ios") or "",
        "min_app_version_android": request.form.get("min_app_version_android") or "",
    }
    try:
        app_config_service.save_operator_settings(**form)
    except ValidationError as err:
        # 고치던 값을 그대로 다시 그린다 — 폼이 비면 운영자가 처음부터 다시 적는다.
        return _render_settings(form, error=err.message)

    flash("설정을 저장했어요. `/config` 캐시를 지웠으니 앱은 다음 호출부터 봅니다.")
    return redirect(url_for("admin.settings_form"))


# --- 영어 책 제목 검색 (Google Books) -----------------------------------


@bp.get("/books")
@admin_required
def books():
    """제목으로 영어 책을 찾아 보여준다. 검색어가 없으면 구글을 부르지 않는다.

    호출 실패를 500 으로 올리지 않는 이유: 구글이 느리거나 쿼터가 찬 건 운영자가
    고칠 수 있는 일이 아니고, 그때도 화면과 다른 메뉴는 살아 있어야 한다.
    """
    keyword = (request.args.get("q") or "").strip()
    results = []
    error = None
    if keyword:
        try:
            results = search_google_books(keyword)
        except requests.RequestException as exc:
            error = f"구글 책 검색에 실패했어요 ({type(exc).__name__}). 잠시 뒤 다시 시도해주세요."

    return render_template(
        "admin/books.html",
        keyword=keyword,
        results=results,
        error=error,
        csrf_token=issue_csrf_token(),
    )


@bp.post("/books")
@admin_required
@csrf_protected
def add_book_word():
    """고른 검색 결과를 en `book_title` 단어로 등록한다. 가림은 모델 이벤트가 계산한다."""
    keyword = (request.form.get("q") or "").strip()
    book = BookSearchResult(
        title=request.form.get("title") or "",
        author=(request.form.get("author") or "").strip() or None,
        publisher=(request.form.get("publisher") or "").strip() or None,
        isbn=(request.form.get("isbn") or "").strip() or None,
        source="google_books",
    )
    try:
        word, created = word_service.add_word_from_book(book, PuzzleLanguage.EN)
    except ValidationError as err:
        flash(err.message)
        return redirect(url_for("admin.books", q=keyword or None))

    if created:
        flash(f"'{word.answer}' 를 영어 책 제목 단어로 추가했어요.")
    else:
        flash(f"'{word.answer}' 는 이미 등록돼 있어요.")
    return redirect(url_for("admin.books", q=keyword or None))


def _read_language(source) -> PuzzleLanguage:
    """언어 탭·폼에서 언어를 읽는다. 모르는 값은 ko 로 둔다 — 손으로 URL 을 고친
    요청 때문에 배정표가 에러 페이지가 되면 안 된다(목록 필터와 같은 규칙)."""
    return _parse_enum(PuzzleLanguage, source.get("language")) or PuzzleLanguage.KO


def _read_schedule_target(raw_date: str) -> tuple[date, PuzzleLanguage]:
    """URL 의 날짜를 배정표 창(오늘~오늘+29일) 안의 날짜로만 받아들인다.

    창 밖(지난 날짜·30일 뒤)은 404 다 — 배정표에서 갈 수 없는 주소이고, 지난
    퍼즐은 기록이라 바꿀 수도 없다(`replace_assignment` 가 다시 막는다).
    """
    source = request.form if request.method == "POST" else request.args
    try:
        target_date = date.fromisoformat(raw_date)
    except ValueError:
        raise NotFoundError() from None

    today = datetime.now(KST).date()
    if not today <= target_date <= today + timedelta(days=SCHEDULE_DAYS - 1):
        raise NotFoundError()

    return target_date, _read_language(source)


def _render_settings(form: dict, error: str | None = None):
    return render_template(
        "admin/settings.html",
        form=form,
        error=error,
        csrf_token=issue_csrf_token(),
    )


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
