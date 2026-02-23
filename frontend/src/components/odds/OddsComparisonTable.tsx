import { Fragment, useMemo } from "react";
import type { OddsSnapshot } from "../../types";

type MarketKey = "h2h" | "spreads" | "totals";

interface BookRow {
  bookmaker: string;
  homeOdds: number | null;
  awayOdds: number | null;
  line: number | null;
}

const MARKET_LABELS: Record<MarketKey, string> = {
  h2h: "Moneyline",
  spreads: "Spread",
  totals: "Total",
};

function formatOdds(odds: number | null) {
  if (odds === null) {
    return "—";
  }
  return odds > 0 ? `+${odds}` : `${odds}`;
}

function isLaterSnapshot(current: OddsSnapshot | undefined, candidate: OddsSnapshot) {
  if (!current) {
    return true;
  }
  return new Date(candidate.snapshot_time).getTime() > new Date(current.snapshot_time).getTime();
}

function resolveHomeAwaySide(snapshot: OddsSnapshot): "home" | "away" | null {
  const side = snapshot.side.toLowerCase();
  const homeTeam = snapshot.home_team.toLowerCase();
  const awayTeam = snapshot.away_team.toLowerCase();

  if (side === "home" || side === homeTeam) {
    return "home";
  }
  if (side === "away" || side === awayTeam) {
    return "away";
  }

  return null;
}

export function OddsComparisonTable({ odds, gameId }: { odds: OddsSnapshot[]; gameId: number | null }) {
  const marketGroups = useMemo(() => {
    const gameOdds = gameId ? odds.filter((snapshot) => snapshot.game_id === gameId) : [];
    const latestByKey = new Map<string, OddsSnapshot>();

    for (const snapshot of gameOdds) {
      const market = snapshot.market as MarketKey;
      if (!(market in MARKET_LABELS)) {
        continue;
      }

      const key = `${market}|${snapshot.bookmaker}|${snapshot.side}`;
      const existing = latestByKey.get(key);
      if (isLaterSnapshot(existing, snapshot)) {
        latestByKey.set(key, snapshot);
      }
    }

    const markets = new Map<MarketKey, Map<string, BookRow>>();

    for (const snapshot of latestByKey.values()) {
      const market = snapshot.market as MarketKey;
      if (!markets.has(market)) {
        markets.set(market, new Map<string, BookRow>());
      }

      const rowsByBook = markets.get(market)!;
      const row = rowsByBook.get(snapshot.bookmaker) ?? {
        bookmaker: snapshot.bookmaker,
        homeOdds: null,
        awayOdds: null,
        line: null,
      };

      if (snapshot.canonical_side === "home") {
        row.homeOdds = snapshot.odds;
      }
      if (snapshot.canonical_side === "away") {
        row.awayOdds = snapshot.odds;
      }
      if (snapshot.line !== null) {
        row.line = snapshot.line;
      }

      rowsByBook.set(snapshot.bookmaker, row);
    }

    return (Object.keys(MARKET_LABELS) as MarketKey[])
      .map((market) => {
        const rows = Array.from(markets.get(market)?.values() ?? []).sort((a, b) => a.bookmaker.localeCompare(b.bookmaker));
        const bestHome = Math.max(...rows.map((row) => row.homeOdds ?? Number.NEGATIVE_INFINITY));
        const bestAway = Math.max(...rows.map((row) => row.awayOdds ?? Number.NEGATIVE_INFINITY));

        return {
          market,
          label: MARKET_LABELS[market],
          rows,
          bestHome,
          bestAway,
        };
      })
      .filter((group) => group.rows.length > 0);
  }, [gameId, odds]);

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-800 bg-gray-900">
      <table className="w-full text-sm">
        <thead className="bg-gray-950 text-gray-400">
          <tr>
            <th className="p-3 text-left">Bookmaker</th>
            <th className="p-3 text-left">Home Odds</th>
            <th className="p-3 text-left">Away Odds</th>
            <th className="p-3 text-left">Line</th>
          </tr>
        </thead>
        <tbody>
          {marketGroups.length === 0 ? (
            <tr className="border-t border-gray-800">
              <td className="p-3 text-gray-500" colSpan={4}>
                Select a game to view odds.
              </td>
            </tr>
          ) : (
            marketGroups.map((group) => (
              <Fragment key={group.market}>
                <tr className="border-t border-gray-800 bg-gray-950/50">
                  <td className="p-3 font-semibold text-gray-200" colSpan={4}>
                    {group.label}
                  </td>
                </tr>
                {group.rows.map((row) => {
                  const isBestHome = row.homeOdds !== null && row.homeOdds === group.bestHome;
                  const isBestAway = row.awayOdds !== null && row.awayOdds === group.bestAway;

                  return (
                    <tr key={`${group.market}-${row.bookmaker}`} className="border-t border-gray-800">
                      <td className="p-3">{row.bookmaker}</td>
                      <td className={`p-3 font-mono ${isBestHome ? "font-semibold text-amber-300" : "text-gray-100"}`}>
                        {formatOdds(row.homeOdds)}
                      </td>
                      <td className={`p-3 font-mono ${isBestAway ? "font-semibold text-emerald-300" : "text-gray-100"}`}>
                        {formatOdds(row.awayOdds)}
                      </td>
                      <td className="p-3 text-gray-300">{row.line ?? "—"}</td>
                    </tr>
                  );
                })}
              </Fragment>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
