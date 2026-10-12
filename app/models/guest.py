import uuid
from datetime import datetime

from app.extensions import db
from app.utils.time import utcnow


class Guest(db.Model):
    __tablename__ = "guest"

    id: int = db.Column(db.Integer, primary_key=True)
    token: str = db.Column(
        db.String(36), nullable=False, unique=True, default=lambda: str(uuid.uuid4())
    )
    created_at: datetime = db.Column(db.DateTime, nullable=False, default=utcnow)
