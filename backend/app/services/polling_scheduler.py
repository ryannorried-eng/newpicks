from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

TOP_8_BOOKS = "draftkings,fanduel,betmgm,caesars,pointsbet,bet365,betrivers,espnbet"


@dataclass
class PollingStatus:
    mode: str = "off_hours"
    active_sports: list[str] = field(default_factory=list)
    quota_remaining: int | None = None
    next_poll_time: datetime | None = None


class AdaptivePollingScheduler:
    def __init__(self) -> None:
        self.status = PollingStatus(next_poll_time=datetime.now(UTC) + timedelta(hours=6))
        self.sport_windows: dict[str, datetime] = {}

    def check_daily_schedule(self, games_by_sport: dict[str, list[datetime]]) -> None:
        now = datetime.now(UTC)
        active = []
        earliest_by_sport: dict[str, datetime] = {}
        for sport, starts in games_by_sport.items():
            upcoming = [dt for dt in starts if dt.date() == now.date()]
            if upcoming:
                active.append(sport)
                earliest_by_sport[sport] = min(upcoming)
        self.status.active_sports = active
        self.sport_windows = earliest_by_sport
        self._recompute_mode(now)

    def update_quota(self, requests_remaining: int | None) -> None:
        self.status.quota_remaining = requests_remaining
        if requests_remaining is not None and requests_remaining < 50:
            self.status.mode = "throttled"
            self.status.next_poll_time = datetime.now(UTC) + timedelta(hours=12)

    def _recompute_mode(self, now: datetime) -> None:
        if not self.status.active_sports:
            self.status.mode = "off_hours"
            self.status.next_poll_time = now + timedelta(hours=6)
            return

        first_game = min(self.sport_windows.values())
        if now >= first_game:
            self.status.mode = "active_window"
            self.status.next_poll_time = now + timedelta(minutes=10)
            return

        if first_game - timedelta(hours=3) <= now < first_game:
            self.status.mode = "pregame_window"
            self.status.next_poll_time = now + timedelta(minutes=15)
            return

        self.status.mode = "off_hours"
        self.status.next_poll_time = now + timedelta(hours=6)

    def poll_bookmakers(self) -> str | None:
        if self.status.mode in {"pregame_window", "active_window"}:
            return TOP_8_BOOKS
        return None

    def get_status(self) -> dict[str, str | int | list[str] | None]:
        return {
            "mode": self.status.mode,
            "active_sports": self.status.active_sports,
            "quota_remaining": self.status.quota_remaining,
            "next_poll_time": self.status.next_poll_time.isoformat() if self.status.next_poll_time else None,
        }


scheduler = AdaptivePollingScheduler()
