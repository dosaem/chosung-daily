from flask import Blueprint, render_template

bp = Blueprint("web", __name__)


@bp.get("/")
def index():
    """게임 화면. 정적 틀만 서버에서 내려주고, 나머지는 vanilla JS가
    /api/v1/*를 호출해서 채운다 (web/static/app.js)."""
    return render_template("index.html")


def register_web(app):
    app.register_blueprint(bp)
