"""phase2 picks table

Revision ID: 0002_phase2
Revises: 0001_phase1
Create Date: 2026-02-22
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_phase2"
down_revision = "0001_phase1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "picks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("games.id"), nullable=False),
        sa.Column("sport_key", sa.String(length=64), nullable=False),
        sa.Column("pick_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("market", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=32), nullable=False),
        sa.Column("line", sa.Float(), nullable=True),
        sa.Column("odds_american", sa.Integer(), nullable=False),
        sa.Column("best_book", sa.String(length=64), nullable=False),
        sa.Column("fair_prob", sa.Float(), nullable=False),
        sa.Column("prob_source", sa.String(length=32), nullable=False, server_default="consensus"),
        sa.Column("implied_prob", sa.Float(), nullable=False),
        sa.Column("ev_pct", sa.Float(), nullable=False),
        sa.Column("composite_score", sa.Float(), nullable=False),
        sa.Column("confidence_tier", sa.String(length=16), nullable=False),
        sa.Column("signals", sa.JSON(), nullable=False),
        sa.Column("data_quality", sa.JSON(), nullable=False),
        sa.Column("suggested_kelly_fraction", sa.Float(), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=True),
        sa.Column("market_clv", sa.Float(), nullable=True),
        sa.Column("book_clv", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("game_id", "market", "side", "pick_date", name="uq_pick_daily_side"),
    )
    op.create_index("ix_picks_sport_key", "picks", ["sport_key"])
    op.create_index("ix_picks_pick_date", "picks", ["pick_date"])
    op.create_index("ix_picks_confidence_tier", "picks", ["confidence_tier"])


def downgrade() -> None:
    op.drop_index("ix_picks_confidence_tier", table_name="picks")
    op.drop_index("ix_picks_pick_date", table_name="picks")
    op.drop_index("ix_picks_sport_key", table_name="picks")
    op.drop_table("picks")
