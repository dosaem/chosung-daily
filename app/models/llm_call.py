from datetime import datetime

from app.extensions import db
from app.models.enums import LlmCallResult
from app.utils.time import utcnow


class LlmCall(db.Model):
    """LLM 호출 한 건의 장부(LLM 출제 파이프라인).

    목적·모델·토큰·비용·지연·결과를 호출마다 남긴다. 월 예산 상한
    (`LLM_MONTHLY_BUDGET_USD`)은 이 테이블의 `cost_usd` 합으로 판정하고, 단어당
    비용·규칙 통과율 같은 운영 수치도 여기서 뽑는다 — 외부 대시보드 없이 SQL 한 줄.

    `cost_usd` 는 호출 시점의 단가표(`app/clients/anthropic.py`)로 계산해 **그때 값을
    굳힌다**. 단가가 바뀌어도 과거 행은 다시 계산하지 않는다(청구서와 맞추려면
    호출 당시 단가가 맞다).
    """

    __tablename__ = "llm_call"

    id: int = db.Column(db.Integer, primary_key=True)
    # 어떤 일로 불렀나: "word_generation" 등. 기능이 늘면 값이 늘어난다.
    purpose: str = db.Column(db.String(40), nullable=False, index=True)
    model: str = db.Column(db.String(60), nullable=False)
    input_tokens: int = db.Column(db.Integer, nullable=False, default=0)
    output_tokens: int = db.Column(db.Integer, nullable=False, default=0)
    # 호출 한 건의 비용(USD). 소수점 6자리면 $0.000001 까지 — 토큰 단가가 그 자리다.
    cost_usd = db.Column(db.Numeric(10, 6), nullable=False, default=0)
    latency_ms: int = db.Column(db.Integer, nullable=False, default=0)
    result: LlmCallResult = db.Column(
        db.Enum(LlmCallResult, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    error: str | None = db.Column(db.String(500), nullable=True)
    # 이 호출이 만든 후보 묶음(word_candidate.batch_id). 생성 목적이 아니면 NULL.
    batch_id: str | None = db.Column(db.String(36), nullable=True, index=True)
    created_at: datetime = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
