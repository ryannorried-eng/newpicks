from __future__ import annotations

from enum import Enum

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.pick import Pick
from app.utils.odds_math import american_to_decimal


class PickOutcome(str, Enum):
    WIN = "win"
    LOSS = "loss"
    PUSH = "push"
    PENDING = "pending"


def _settle_h2h(pick: Pick, game: Game) -> PickOutcome:
    if game.home_score == game.away_score:
        return PickOutcome.PUSH
    winner = game.home_team if game.home_score > game.away_score else game.away_team
    return PickOutcome.WIN if pick.side.strip().lower() == winner.strip().lower() else PickOutcome.LOSS


def _settle_spread(pick: Pick, game: Game) -> PickOutcome:
    if pick.line is None:
        return PickOutcome.PENDING
    side = pick.side.strip().lower()
    home = game.home_team.strip().lower()
    away = game.away_team.strip().lower()

    if side == home:
        lhs = game.home_score + pick.line
        rhs = game.away_score
    elif side == away:
        lhs = game.away_score + pick.line
        rhs = game.home_score
    else:
        return PickOutcome.PENDING

    if lhs > rhs:
        return PickOutcome.WIN
    if lhs < rhs:
        return PickOutcome.LOSS
    return PickOutcome.PUSH


def _settle_total(pick: Pick, game: Game) -> PickOutcome:
    if pick.line is None:
        return PickOutcome.PENDING
    total = game.home_score + game.away_score
    side = pick.side.strip().lower()
    if total == pick.line:
        return PickOutcome.PUSH
    if side == "over":
        return PickOutcome.WIN if total > pick.line else PickOutcome.LOSS
    if side == "under":
        return PickOutcome.WIN if total < pick.line else PickOutcome.LOSS
    return PickOutcome.PENDING


async def settle_picks(session: AsyncSession) -> dict:
    picks = (
        await session.scalars(
            select(Pick)
            .join(Game, Pick.game_id == Game.id)
            .where(
                and_(
                    Game.completed.is_(True),
                    (Pick.outcome.is_(None)) | (Pick.outcome == PickOutcome.PENDING.value),
                )
            )
        )
    ).all()

    settled = wins = losses = pushes = 0
    for pick in picks:
        game = await session.scalar(select(Game).where(Game.id == pick.game_id))
        if game is None or game.home_score is None or game.away_score is None:
            continue

        if pick.market == "h2h":
            outcome = _settle_h2h(pick, game)
        elif pick.market == "spreads":
            outcome = _settle_spread(pick, game)
        elif pick.market == "totals":
            outcome = _settle_total(pick, game)
        else:
            continue

        if outcome == PickOutcome.PENDING:
            continue

        stake = pick.suggested_kelly_fraction
        if outcome == PickOutcome.WIN:
            pick.profit_loss = (american_to_decimal(pick.odds_american) - 1.0) * stake
            wins += 1
        elif outcome == PickOutcome.LOSS:
            pick.profit_loss = -1.0 * stake
            losses += 1
        else:
            pick.profit_loss = 0.0
            pushes += 1

        pick.outcome = outcome.value
        settled += 1

    await session.commit()
    return {"settled": settled, "wins": wins, "losses": losses, "pushes": pushes}
