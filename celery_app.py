from celery import Celery
from celery.schedules import crontab

from app import create_app

flask_app = create_app()


def make_celery(app) -> Celery:
    """Flask 앱 컨텍스트 안에서 태스크가 돌게 감싼다.

    Celery worker/beat는 Flask 요청-응답 밖에서 돌기 때문에, db.session이나
    current_app을 쓰려면 매 태스크마다 app context를 직접 열어야 한다.
    """
    celery = Celery(app.import_name, broker=app.config["REDIS_URL"])
    celery.conf.timezone = "Asia/Seoul"

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


celery = make_celery(flask_app)

celery.conf.beat_schedule = {
    "ensure-today-puzzle": {
        "task": "tasks.ensure_today_puzzle",
        "schedule": crontab(hour=0, minute=0),
    },
    "flush-daily-stats": {
        "task": "tasks.flush_daily_stats",
        "schedule": crontab(hour=0, minute=5),
    },
}

from app.tasks import scheduled  # noqa: E402,F401  (celery가 정의된 뒤에 태스크를 등록해야 함)
