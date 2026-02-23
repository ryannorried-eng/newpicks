import { Fragment, useMemo } from "react";
import type { OddsSnapshot } from "../../types";

type MarketKey = "h2h" | "spreads" | "totals";
type TeamBucketKey = "home" | "away";
type TotalsBucketKey = "over" | "under";
type BucketKey = TeamBucketKey | TotalsBucketKey | "unknown";

interface BucketValue {
  odds: number;
  line: number | null;
}

interface BookRow {
  bookmaker: string;
  buckets: Partial<Record<BucketKey, BucketValue>>;
}

const MARKET_LABELS: Record<MarketKey, string> = {
  h2h: "Moneyline",
  spreads: "Spread",
  totals: "Total",
};

function norm(s: string | null | undefined): string {
  return (s ?? "").trim().toLowerCase();
}

function isTeamMarket(market: string): boolean {
  return market === "h2h" || market === "spreads";
}


function snapshotBucket(snapshot: OddsSnapshot, market: MarketKey): BucketKey {
  if (isTeamMarket(market)) {
    return snapshot.canonical_side ?? "unknown";
  }
  const side = norm(snapshot.side);
  if (side === "over" || side === "under") {
    return side;
  }
  return "unknown";
}

function formatOdds(odds: number) {
  return odds > 0 ? `+${odds}` : `${odds}`;
}

function formatBucketCell(value?: BucketValue) {
  if (!value) {
    return "—";
  }

  if (value.line === null) {
    return formatOdds(value.odds);
  }

  return `${formatOdds(value.odds)} (${value.line})`;
}

function isLaterSnapshot(current: OddsSnapshot | undefined, candidate: OddsSnapshot) {
  if (!current) {
    return true;
  }
  return new Date(candidate.snapshot_time).getTime() > new Date(current.snapshot_time).getTime();
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

      const bucket = snapshotBucket(snapshot, market);
      const baseKey = `${snapshot.game_id}|${snapshot.bookmaker}|${market}`;
      const key = `${baseKey}|${bucket}`;
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
        buckets: {},
      };

      const bucket = snapshotBucket(snapshot, market);
      row.buckets[bucket] = {
        odds: snapshot.odds,
        line: snapshot.line,
      };

      rowsByBook.set(snapshot.bookmaker, row);
    }

    return (Object.keys(MARKET_LABELS) as MarketKey[])
      .map((market) => {
        const rows = Array.from(markets.get(market)?.values() ?? []).sort((a, b) => a.bookmaker.localeCompare(b.bookmaker));
        const firstBucket: TeamBucketKey | TotalsBucketKey = isTeamMarket(market) ? "home" : "over";
        const secondBucket: TeamBucketKey | TotalsBucketKey = isTeamMarket(market) ? "away" : "under";
        const bestFirst = Math.max(...rows.map((row) => row.buckets[firstBucket]?.odds ?? Number.NEGATIVE_INFINITY));
        const bestSecond = Math.max(...rows.map((row) => row.buckets[secondBucket]?.odds ?? Number.NEGATIVE_INFINITY));

        return {
          market,
          label: MARKET_LABELS[market],
          firstHeader: isTeamMarket(market) ? "Home" : "Over",
          secondHeader: isTeamMarket(market) ? "Away" : "Under",
          firstBucket,
          secondBucket,
          rows,
          bestFirst,
          bestSecond,
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
            <th className="p-3 text-left">Side 1</th>
            <th className="p-3 text-left">Side 2</th>
          </tr>
        </thead>
        <tbody>
          {marketGroups.length === 0 ? (
            <tr className="border-t border-gray-800">
              <td className="p-3 text-gray-500" colSpan={3}>
                Select a game to view odds.
              </td>
            </tr>
          ) : (
            marketGroups.map((group) => (
              <Fragment key={group.market}>
                <tr className="border-t border-gray-800 bg-gray-950/50">
                  <td className="p-3 font-semibold text-gray-200">{group.label}</td>
                  <td className="p-3 font-semibold text-gray-300">{group.firstHeader}</td>
                  <td className="p-3 font-semibold text-gray-300">{group.secondHeader}</td>
                </tr>
                {group.rows.map((row) => {
                  const homeRow = row.buckets["home"];
                  const awayRow = row.buckets["away"];
                  const overRow = row.buckets["over"];
                  const underRow = row.buckets["under"];
                  const first = isTeamMarket(group.market) ? homeRow : overRow;
                  const second = isTeamMarket(group.market) ? awayRow : underRow;
                  const isBestFirst = first?.odds !== undefined && first.odds === group.bestFirst;
                  const isBestSecond = second?.odds !== undefined && second.odds === group.bestSecond;

                  return (
                    <tr key={`${group.market}-${row.bookmaker}`} className="border-t border-gray-800">
                      <td className="p-3">{row.bookmaker}</td>
                      <td className={`p-3 font-mono ${isBestFirst ? "font-semibold text-amber-300" : "text-gray-100"}`}>
                        {formatBucketCell(first)}
                      </td>
                      <td className={`p-3 font-mono ${isBestSecond ? "font-semibold text-emerald-300" : "text-gray-100"}`}>
                        {formatBucketCell(second)}
                      </td>
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
