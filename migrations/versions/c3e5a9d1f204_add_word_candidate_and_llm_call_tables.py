"""add word_candidate and llm_call tables

LLM 출제 파이프라인. `word_candidate` 는 LLM 이 만든 후보와 처리 상태(승인 대기·
승인·탈락 + 사유), `llm_call` 은 호출마다 토큰·비용·지연·결과 장부다.

조회 축: 승인 대기 목록(`status`), 배치별 통과율(`batch_id`), 월 예산 합계와
단어당 비용(`llm_call.created_at`, `purpose`) — 인덱스는 그 축만 둔다.

Revision ID: c3e5a9d1f204
Revises: b1c7d4e0a932
Create Date: 2026-10-16 14:10:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c3e5a9d1f204"
down_revision = "b1c7d4e0a932"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "llm_call",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("purpose", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=60), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column(
            "result", sa.Enum("success", "failure", "retried", name="llmcallresult"), nullable=False
        ),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column("batch_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("llm_call", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_llm_call_batch_id"), ["batch_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_llm_call_created_at"), ["created_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_llm_call_purpose"), ["purpose"], unique=False)

    op.create_table(
        "word_candidate",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("language", sa.Enum("ko", "en", name="puzzlelanguage"), nullable=False),
        sa.Column(
            "category", sa.Enum("general", "book_title", name="wordcategory"), nullable=False
        ),
        sa.Column("answer", sa.String(length=50), nullable=False),
        sa.Column("hint", sa.String(length=200), nullable=False),
        sa.Column(
            "status",
            sa.Enum("proposed", "approved", "rejected", name="candidatestatus"),
            nullable=False,
        ),
        sa.Column("reject_reason", sa.String(length=300), nullable=True),
        sa.Column("batch_id", sa.String(length=36), nullable=False),
        sa.Column("reviewed_by", sa.String(length=191), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("word_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["word_id"],
            ["word.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("word_candidate", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_word_candidate_batch_id"), ["batch_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_word_candidate_status"), ["status"], unique=False)


def downgrade():
    with op.batch_alter_table("word_candidate", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_word_candidate_status"))
        batch_op.drop_index(batch_op.f("ix_word_candidate_batch_id"))
    op.drop_table("word_candidate")

    with op.batch_alter_table("llm_call", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_llm_call_purpose"))
        batch_op.drop_index(batch_op.f("ix_llm_call_created_at"))
        batch_op.drop_index(batch_op.f("ix_llm_call_batch_id"))
    op.drop_table("llm_call")
