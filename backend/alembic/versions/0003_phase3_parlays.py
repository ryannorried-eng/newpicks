"""phase3 parlays tables

Revision ID: 0003_phase3
Revises: 0002_phase2
Create Date: 2026-02-22
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_phase3"
down_revision = "0002_phase2"
branch_labels = None
depends_on = None


def _has_table(bind, name: str) -> bool:
    inspector = sa.inspect(bind)
    return inspector.has_table(name)


def _has_column(bind, table: str, col: str) -> bool:
    inspector = sa.inspect(bind)
    return col in {c["name"] for c in inspector.get_columns(table)}


def _has_index(bind, table: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(ix["name"] == index_name for ix in inspector.get_indexes(table))


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind, "parlays"):
        op.create_table(
            "parlays",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("risk_level", sa.String(length=32), nullable=False),
            sa.Column("num_legs", sa.Integer(), nullable=False),
            sa.Column("combined_odds_american", sa.Integer(), nullable=False),
            sa.Column("combined_odds_decimal", sa.Float(), nullable=False),
            sa.Column("combined_ev_pct", sa.Float(), nullable=False),
            sa.Column("combined_fair_prob", sa.Float(), nullable=False),
            sa.Column("correlation_score", sa.Float(), nullable=False),
            sa.Column("suggested_kelly_fraction", sa.Float(), nullable=False),
            sa.Column("outcome", sa.String(length=16), nullable=False, server_default="pending"),
            sa.Column("profit_loss", sa.Float(), nullable=True),
            sa.Column("pick_date", sa.Date(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.UniqueConstraint("risk_level", "pick_date", "combined_odds_american", name="uq_parlay_daily_exact"),
        )
    else:
        for name, coltype, nullable, server_default in [
            ("combined_odds_american", sa.Integer(), False, None),
            ("combined_odds_decimal", sa.Float(), False, None),
            ("combined_ev_pct", sa.Float(), False, None),
            ("combined_fair_prob", sa.Float(), False, None),
            ("outcome", sa.String(length=16), False, "pending"),
            ("profit_loss", sa.Float(), True, None),
            ("pick_date", sa.Date(), False, None),
        ]:
            if not _has_column(bind, "parlays", name):
                op.add_column("parlays", sa.Column(name, coltype, nullable=nullable, server_default=server_default))

    if not _has_index(bind, "parlays", "ix_parlays_pick_date_risk"):
        op.create_index("ix_parlays_pick_date_risk", "parlays", ["pick_date", "risk_level"])

    if not _has_table(bind, "parlay_legs"):
        op.create_table(
            "parlay_legs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("parlay_id", sa.Integer(), sa.ForeignKey("parlays.id"), nullable=False),
            sa.Column("pick_id", sa.Integer(), sa.ForeignKey("picks.id"), nullable=False),
            sa.Column("leg_order", sa.Integer(), nullable=False),
            sa.Column("result", sa.String(length=16), nullable=False, server_default="pending"),
        )
    else:
        if not _has_column(bind, "parlay_legs", "result"):
            op.add_column("parlay_legs", sa.Column("result", sa.String(length=16), nullable=False, server_default="pending"))


def downgrade() -> None:
    bind = op.get_bind()
    if _has_index(bind, "parlays", "ix_parlays_pick_date_risk"):
        op.drop_index("ix_parlays_pick_date_risk", table_name="parlays")
