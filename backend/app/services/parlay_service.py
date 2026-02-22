from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import combinations

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.compatibility import check_compatibility
from app.analytics.correlation import adjusted_joint_probability, estimate_correlation
from app.models.parlay import Parlay, ParlayLeg
from app.models.pick import Pick
from app.utils.odds_math import (
    american_to_decimal,
    calculate_ev,
    calculate_parlay_odds,
    decimal_to_american,
    kelly_criterion,
)


@dataclass
class ParlayCandidate:
    legs: list[Pick]
    num_legs: int
    combined_fair_prob: float
    combined_odds_decimal: float
    combined_odds_american: int
    combined_ev_pct: float
    correlation_score: float
    risk_level: str
    suggested_kelly_fraction: float


RISK_CONFIGS = {
    "conservative": {
        "min_legs": 2,
        "max_legs": 3,
        "allowed_confidence": ["high"],
        "min_combined_odds_american": 150,
        "max_combined_odds_american": 300,
        "max_correlation": 0.15,
    },
    "moderate": {
        "min_legs": 3,
        "max_legs": 4,
        "allowed_confidence": ["high", "medium"],
        "min_combined_odds_american": 300,
        "max_combined_odds_american": 800,
        "max_correlation": 0.40,
    },
    "aggressive": {
        "min_legs": 4,
        "max_legs": 6,
        "allowed_confidence": ["high", "medium", "low"],
        "min_combined_odds_american": 800,
        "max_combined_odds_american": 2500,
        "max_correlation": 0.70,
    },
}


def _avg_pairwise_corr(legs: list[Pick]) -> float:
    pairs = [estimate_correlation(a, b) for a, b in combinations(legs, 2)]
    return sum(pairs) / len(pairs) if pairs else 0.0


def _joint_prob(legs: list[Pick]) -> float:
    if not legs:
        return 0.0
    prob = legs[0].fair_prob
    for leg in legs[1:]:
        corr = estimate_correlation(legs[0], leg)
        prob = adjusted_joint_probability(prob, leg.fair_prob, corr)
    return max(0.0, min(1.0, prob))


def _candidate_from_legs(legs: list[Pick], risk_level: str) -> ParlayCandidate:
    combined_decimal = calculate_parlay_odds([american_to_decimal(p.odds_american) for p in legs])
    combined_american = decimal_to_american(combined_decimal)
    fair_prob = _joint_prob(legs)
    combined_ev = calculate_ev(fair_prob, combined_decimal)
    corr = _avg_pairwise_corr(legs)
    kelly = kelly_criterion(fair_prob, combined_decimal, fraction=0.15)
    return ParlayCandidate(
        legs=legs,
        num_legs=len(legs),
        combined_fair_prob=fair_prob,
        combined_odds_decimal=combined_decimal,
        combined_odds_american=combined_american,
        combined_ev_pct=combined_ev,
        correlation_score=corr,
        risk_level=risk_level,
        suggested_kelly_fraction=kelly,
    )


def _is_valid_candidate(candidate: ParlayCandidate, risk_level: str) -> bool:
    cfg = RISK_CONFIGS[risk_level]
    if not (cfg["min_combined_odds_american"] <= candidate.combined_odds_american <= cfg["max_combined_odds_american"]):
        return False
    if candidate.correlation_score > cfg["max_correlation"]:
        return False
    if candidate.combined_ev_pct <= 0:
        return False
    return True


async def build_parlays_for_risk_level(
    picks: list[Pick],
    risk_level: str,
    session: AsyncSession,
    max_parlays: int = 3,
) -> list[ParlayCandidate]:
    _ = session
    cfg = RISK_CONFIGS[risk_level]
    pool = [p for p in picks if p.confidence_tier in cfg["allowed_confidence"]]
    if len(pool) < cfg["min_legs"]:
        return []

    pool = sorted(pool, key=lambda x: x.ev_pct, reverse=True)
    candidates: list[ParlayCandidate] = []

    for size in range(cfg["min_legs"], cfg["max_legs"] + 1):
        if len(pool) < size:
            continue

        # Greedy seed
        selected = [pool[0]]
        for cand in pool[1:]:
            if len(selected) >= size:
                break
            compat_ok = all(check_compatibility(leg, cand, risk_level).is_compatible for leg in selected)
            if compat_ok:
                selected.append(cand)
        if len(selected) == size:
            c = _candidate_from_legs(selected, risk_level)
            if _is_valid_candidate(c, risk_level):
                candidates.append(c)

        # brute force for small combos
        if size <= 3:
            for combo in combinations(pool, size):
                if all(check_compatibility(a, b, risk_level).is_compatible for a, b in combinations(combo, 2)):
                    c = _candidate_from_legs(list(combo), risk_level)
                    if _is_valid_candidate(c, risk_level):
                        candidates.append(c)

    # de-dup by sorted pick ids
    unique: dict[tuple[int, ...], ParlayCandidate] = {}
    for c in candidates:
        key = tuple(sorted(p.id for p in c.legs))
        if key not in unique or c.combined_ev_pct > unique[key].combined_ev_pct:
            unique[key] = c

    ranked = sorted(unique.values(), key=lambda c: c.combined_ev_pct, reverse=True)
    return ranked[:max_parlays]


async def generate_daily_parlays(session: AsyncSession) -> list[Parlay]:
    now = datetime.now(UTC)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    pick_date = day_start.date()

    day_end = day_start.replace(hour=23, minute=59, second=59, microsecond=999999)
    today_picks = (
        await session.scalars(
            select(Pick).where(and_(Pick.pick_date >= day_start, Pick.pick_date <= day_end)).order_by(Pick.ev_pct.desc())
        )
    ).all()

    if len(today_picks) < 2:
        return []

    await session.execute(delete(Parlay).where(Parlay.pick_date == pick_date))

    generated_rows: list[Parlay] = []
    for risk_level in ("conservative", "moderate", "aggressive"):
        candidates = await build_parlays_for_risk_level(today_picks, risk_level, session, max_parlays=3)
        for cand in candidates:
            row = Parlay(
                risk_level=risk_level,
                num_legs=cand.num_legs,
                combined_odds_american=cand.combined_odds_american,
                combined_odds_decimal=cand.combined_odds_decimal,
                combined_ev_pct=cand.combined_ev_pct,
                combined_fair_prob=cand.combined_fair_prob,
                correlation_score=cand.correlation_score,
                suggested_kelly_fraction=cand.suggested_kelly_fraction,
                pick_date=pick_date,
                outcome="pending",
            )
            session.add(row)
            await session.flush()
            for idx, pick in enumerate(cand.legs, start=1):
                session.add(ParlayLeg(parlay_id=row.id, pick_id=pick.id, leg_order=idx, result="pending"))
            generated_rows.append(row)

    await session.commit()
    return generated_rows


async def build_custom_parlay(session: AsyncSession, pick_ids: list[int]) -> dict:
    if len(pick_ids) < 2:
        return {"is_valid": False, "reason": "at_least_two_picks_required"}
    picks = (await session.scalars(select(Pick).where(Pick.id.in_(pick_ids)))).all()
    if len(picks) != len(set(pick_ids)):
        return {"is_valid": False, "reason": "pick_not_found"}

    warnings: list[str] = []
    for a, b in combinations(picks, 2):
        r = check_compatibility(a, b, "aggressive")
        if not r.is_compatible:
            return {"is_valid": False, "reason": r.reason, "compatibility_warnings": [r.reason]}
        corr = estimate_correlation(a, b)
        if corr > 0.40:
            warnings.append(f"high_pair_correlation:{a.id}-{b.id}:{corr:.2f}")

    cand = _candidate_from_legs(picks, "aggressive")
    return {
        "is_valid": True,
        "reason": "",
        "combined_odds_american": cand.combined_odds_american,
        "combined_odds_decimal": cand.combined_odds_decimal,
        "combined_ev_pct": cand.combined_ev_pct,
        "combined_fair_prob": cand.combined_fair_prob,
        "correlation_score": cand.correlation_score,
        "compatibility_warnings": warnings,
        "suggested_kelly_fraction": cand.suggested_kelly_fraction,
    }
