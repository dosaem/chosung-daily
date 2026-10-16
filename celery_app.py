from celery import Celery

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

# 태스크 모듈은 import 되는 것만으로 자기 태스크와 Beat 스케줄을 등록한다
# (app/tasks/scheduled.py 끝의 beat_schedule 합치기). celery가 정의된 뒤에 와야 한다.
from app.tasks import llm, scheduled  # noqa: E402,F401
