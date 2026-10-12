from app.extensions import db
from app.models import Guest


def find_by_token(token: str) -> Guest | None:
    return db.session.query(Guest).filter_by(token=token).first()
