"""phase6 model driven picks and clv fields

Revision ID: 0005_phase6
Revises: 0004_phase5
Create Date: 2026-02-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_phase6"
down_revision = "0004_phase5"
branch_labels = None
depends_on = None


def _has_column(bind, table: str, col: str) -> bool:
    inspector = sa.inspect(bind)
    return col in {c["name"] for c in inspector.get_columns(table)}


def _has_unique(bind, table: str, name: str) -> bool:
    inspector = sa.inspect(bind)
    return name in {c["name"] for c in inspector.get_unique_constraints(table)}


def upgrade() -> None:
    bind = op.get_bind()

    add_cols = [
        ("issued_at", sa.DateTime(timezone=True), False, sa.text("now()")),
        ("snapshot_time_open", sa.DateTime(timezone=True), True, None),
        ("model_prob", sa.Float(), True, None),
        ("implied_prob_open", sa.Float(), True, None),
        ("edge", sa.Float(), True, None),
        ("consensus_prob", sa.Float(), True, None),
        ("book_count", sa.Integer(), True, None),
        ("closing_odds_american", sa.Integer(), True, None),
        ("closing_line", sa.Float(), True, None),
        ("closing_snapshot_time", sa.DateTime(timezone=True), True, None),
        ("clv_prob", sa.Float(), True, None),
        ("clv_price", sa.Float(), True, None),
        ("status", sa.String(length=16), False, sa.text("'open'")),
        ("result", sa.String(length=8), True, None),
        ("settled_at", sa.DateTime(timezone=True), True, None),
        ("pnl_units", sa.Float(), True, None),
        ("pick_day", sa.Date(), True, None),
    ]

    for name, typ, nullable, server_default in add_cols:
        if not _has_column(bind, "picks", name):
            op.add_column("picks", sa.Column(name, typ, nullable=nullable, server_default=server_default))

    op.execute("UPDATE picks SET pick_day = DATE(pick_date) WHERE pick_day IS NULL")
    op.alter_column("picks", "pick_day", nullable=False)

    if not _has_unique(bind, "picks", "uq_pick_game_market_side_day"):
        op.create_unique_constraint(
            "uq_pick_game_market_side_day",
            "picks",
            ["game_id", "market", "side", "pick_day"],
        )


def downgrade() -> None:
    pass
