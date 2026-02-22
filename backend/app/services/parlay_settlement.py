from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.parlay import Parlay, ParlayLeg


async def settle_parlays(session: AsyncSession) -> dict:
    parlays = (
        await session.scalars(
            select(Parlay).where(Parlay.outcome == "pending").options(selectinload(Parlay.legs).selectinload(ParlayLeg.pick))
        )
    ).all()

    settled = wins = losses = pushes = 0
    for parlay in parlays:
        leg_outcomes = [leg.pick.outcome for leg in parlay.legs if leg.pick is not None]
        if not leg_outcomes or any(o in (None, "pending") for o in leg_outcomes):
            continue

        for leg in parlay.legs:
            if leg.pick is not None and leg.pick.outcome:
                leg.result = leg.pick.outcome

        if all(o == "push" for o in leg_outcomes):
            parlay.outcome = "push"
            parlay.profit_loss = 0.0
            pushes += 1
        elif any(o == "loss" for o in leg_outcomes):
            parlay.outcome = "loss"
            parlay.profit_loss = -1.0 * parlay.suggested_kelly_fraction
            losses += 1
        else:
            parlay.outcome = "win"
            parlay.profit_loss = (parlay.combined_odds_decimal - 1.0) * parlay.suggested_kelly_fraction
            wins += 1

        settled += 1

    await session.commit()
    return {"settled": settled, "wins": wins, "losses": losses, "pushes": pushes}
