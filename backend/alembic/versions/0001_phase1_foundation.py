"""phase1 foundation

Revision ID: 0001_phase1
Revises:
Create Date: 2026-02-22
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_phase1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("sport_id", sa.Integer(), sa.ForeignKey("sports.id"), nullable=False),
        sa.Column("home_team", sa.String(length=128), nullable=False),
        sa.Column("away_team", sa.String(length=128), nullable=False),
        sa.Column("commence_time", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "odds_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("games.id"), nullable=False),
        sa.Column("sport_key", sa.String(length=64), nullable=False),
        sa.Column("bookmaker", sa.String(length=64), nullable=False),
        sa.Column("market", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=32), nullable=False),
        sa.Column("line", sa.Float(), nullable=True),
        sa.Column("odds", sa.Integer(), nullable=False),
        sa.Column("implied_prob", sa.Float(), nullable=False),
        sa.Column("no_vig_prob", sa.Float(), nullable=False),
        sa.Column("commence_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot_time", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("snapshot_time_rounded", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_closing", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint(
            "game_id",
            "bookmaker",
            "market",
            "side",
            "snapshot_time_rounded",
            name="uq_odds_snapshot_minute",
        ),
    )

    op.create_index("ix_odds_sport_commence", "odds_snapshots", ["sport_key", "commence_time"])
    op.create_index("ix_odds_game_market_time", "odds_snapshots", ["game_id", "market", "snapshot_time"])
    op.create_index("ix_odds_book_market_time", "odds_snapshots", ["bookmaker", "market", "snapshot_time"])
    op.create_index(
        "ix_odds_game_book_market_side",
        "odds_snapshots",
        ["game_id", "bookmaker", "market", "side", "snapshot_time"],
    )
    # Future optimization note: add native daily range partitioning on snapshot_time once table exceeds 1M rows.


def downgrade() -> None:
    op.drop_index("ix_odds_game_book_market_side", table_name="odds_snapshots")
    op.drop_index("ix_odds_book_market_time", table_name="odds_snapshots")
    op.drop_index("ix_odds_game_market_time", table_name="odds_snapshots")
    op.drop_index("ix_odds_sport_commence", table_name="odds_snapshots")
    op.drop_table("odds_snapshots")
    op.drop_table("games")
    op.drop_table("sports")
