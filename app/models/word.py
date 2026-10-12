from datetime import datetime

from sqlalchemy import event

from app.extensions import db
from app.models.enums import WordCategory
from app.utils.chosung import extract_chosung
from app.utils.time import utcnow


class Word(db.Model):
    __tablename__ = "word"

    id: int = db.Column(db.Integer, primary_key=True)
    answer: str = db.Column(db.String(50), nullable=False)
    chosung: str = db.Column(db.String(50), nullable=False)
    category: WordCategory = db.Column(
        db.Enum(WordCategory, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    hint: str = db.Column(db.String(200), nullable=False)
    created_at: datetime = db.Column(db.DateTime, nullable=False, default=utcnow)


@event.listens_for(Word, "before_insert")
@event.listens_for(Word, "before_update")
def _set_chosung(_mapper, _connection, target: Word) -> None:
    """answer 저장 전 chosung을 항상 다시 계산한다. Spring의 @PrePersist/@PreUpdate 대응."""
    target.chosung = extract_chosung(target.answer)
