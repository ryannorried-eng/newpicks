"""phase5 settlement and performance

Revision ID: 0004_phase5
Revises: 0003_phase3
Create Date: 2026-02-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004_phase5"
down_revision = "0003_phase3"
branch_labels = None
depends_on = None


def _has_table(bind, name: str) -> bool:
    inspector = sa.inspect(bind)
    return inspector.has_table(name)


def _has_column(bind, table: str, col: str) -> bool:
    inspector = sa.inspect(bind)
    return col in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()

    for col, coltype, default in [
        ("home_score", sa.Integer(), None),
        ("away_score", sa.Integer(), None),
        ("completed", sa.Boolean(), sa.text("false")),
        ("result_fetched", sa.Boolean(), sa.text("false")),
    ]:
        if not _has_column(bind, "games", col):
            op.add_column("games", sa.Column(col, coltype, nullable=True if default is None else False, server_default=default))

    if not _has_column(bind, "picks", "profit_loss"):
        op.add_column("picks", sa.Column("profit_loss", sa.Float(), nullable=True))

    if not _has_table(bind, "bankroll_entries"):
        op.create_table(
            "bankroll_entries",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("pick_id", sa.Integer(), sa.ForeignKey("picks.id"), nullable=True),
            sa.Column("entry_type", sa.String(length=32), nullable=False),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("balance_after", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index("ix_bankroll_entries_pick_id", "bankroll_entries", ["pick_id"])

    if not _has_table(bind, "performance_snapshots"):
        op.create_table(
            "performance_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("snapshot_date", sa.Date(), nullable=False, unique=True),
            sa.Column("total_picks", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("settled_picks", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("pushes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("win_rate", sa.Float(), nullable=False, server_default="0"),
            sa.Column("roi_pct", sa.Float(), nullable=False, server_default="0"),
            sa.Column("total_profit_units", sa.Float(), nullable=False, server_default="0"),
            sa.Column("avg_ev_pct", sa.Float(), nullable=False, server_default="0"),
            sa.Column("avg_market_clv", sa.Float(), nullable=False, server_default="0"),
            sa.Column("avg_book_clv", sa.Float(), nullable=False, server_default="0"),
            sa.Column("by_sport", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("by_market", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("by_tier", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )


def downgrade() -> None:
    pass
