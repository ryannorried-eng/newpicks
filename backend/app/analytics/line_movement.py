from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Any


def _direction(delta: int) -> str:
    if delta < 0:
        return "shorter"
    if delta > 0:
        return "longer"
    return "flat"


def detect_steam_move(game_id: int, market: str, side: str, snapshots: list[Any]) -> dict | None:
    snaps = sorted(
        [s for s in snapshots if s.game_id == game_id and s.market == market and s.side == side],
        key=lambda x: x.snapshot_time,
    )
    if len(snaps) < 3:
        return None

    moves = defaultdict(list)
    for i in range(1, len(snaps)):
        prev, cur = snaps[i - 1], snaps[i]
        if cur.bookmaker != prev.bookmaker:
            continue
        delta = cur.odds - prev.odds
        if delta != 0:
            moves[cur.bookmaker].append((cur.snapshot_time, _direction(delta)))

    window = timedelta(minutes=30)
    for direction in ("shorter", "longer"):
        matching_books = []
        times = []
        for book, events in moves.items():
            for t, d in events:
                if d == direction:
                    matching_books.append(book)
                    times.append(t)
                    break
        if len(set(matching_books)) >= 3 and (max(times) - min(times)) <= window:
            return {"detected": True, "books_moved": sorted(set(matching_books)), "direction": direction, "window_minutes": 30}

    return None


def detect_reverse_line_movement(game_id: int, market: str, side: str, snapshots: list[Any]) -> dict | None:
    snaps = sorted([s for s in snapshots if s.game_id == game_id and s.market == market and s.side == side], key=lambda x: x.snapshot_time)
    if len(snaps) < 4:
        return None

    by_book = defaultdict(list)
    for s in snaps:
        by_book[s.bookmaker].append(s)

    book_dirs = []
    for items in by_book.values():
        if len(items) < 2:
            continue
        delta = items[-1].odds - items[0].odds
        if delta != 0:
            book_dirs.append(_direction(delta))

    if len(book_dirs) < 2:
        return None

    expected = "shorter" if book_dirs.count("shorter") >= book_dirs.count("longer") else "longer"
    avg_open = sum(by_book[b][0].odds for b in by_book if by_book[b]) / len(by_book)
    avg_now = sum(by_book[b][-1].odds for b in by_book if by_book[b]) / len(by_book)
    actual = _direction(int(avg_now - avg_open))

    if expected != actual and actual != "flat":
        return {"detected": True, "expected_direction": expected, "actual_direction": actual}
    return None


def detect_line_freeze(game_id: int, market: str, snapshots: list[Any]) -> dict | None:
    snaps = sorted([s for s in snapshots if s.game_id == game_id and s.market == market], key=lambda x: x.snapshot_time)
    if len(snaps) < 6:
        return None
    minutes = int((snaps[-1].snapshot_time - snaps[0].snapshot_time).total_seconds() / 60)
    if minutes < 30:
        return None
    odds_values = {s.odds for s in snaps}
    if len(odds_values) == 1:
        return {"detected": True, "frozen_minutes": minutes}
    return None


def get_opening_to_current_change(game_id: int, market: str, side: str, snapshots: list[Any]) -> dict:
    snaps = sorted([s for s in snapshots if s.game_id == game_id and s.market == market and s.side == side], key=lambda x: x.snapshot_time)
    if not snaps:
        return {"opening_odds": 0, "current_odds": 0, "change": 0, "direction": "flat"}
    opening = snaps[0].odds
    current = snaps[-1].odds
    change = current - opening
    return {"opening_odds": opening, "current_odds": current, "change": change, "direction": _direction(change)}
