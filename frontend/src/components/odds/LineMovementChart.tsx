import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { OddsSnapshot } from "../../types";

function isLatestSnapshot(current: OddsSnapshot | undefined, candidate: OddsSnapshot) {
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

export function LineMovementChart({ odds, gameId }: { odds: OddsSnapshot[]; gameId: number | null }) {
  const gameOdds = useMemo(() => (gameId ? odds.filter((o) => o.game_id === gameId) : []), [gameId, odds]);

  const matchupTitle = useMemo(() => {
    if (!gameOdds.length) {
      return "Moneyline Comparison";
    }

    const latestGameSnapshot = [...gameOdds].sort(
      (a, b) => new Date(b.snapshot_time).getTime() - new Date(a.snapshot_time).getTime(),
    )[0];
    return `Moneyline Comparison — ${latestGameSnapshot.away_team} @ ${latestGameSnapshot.home_team}`;
  }, [gameOdds]);

  const moneylineRows = useMemo(() => {
    const h2hOdds = gameOdds.filter((snapshot) => snapshot.market === "h2h");
    const latestByBookAndSide = new Map<string, OddsSnapshot>();

    for (const snapshot of h2hOdds) {
      const key = `${snapshot.bookmaker}|${snapshot.side}`;
      const existing = latestByBookAndSide.get(key);
      if (isLatestSnapshot(existing, snapshot)) {
        latestByBookAndSide.set(key, snapshot);
      }
    }

    const byBook = new Map<string, { bookmaker: string; homeOdds: number | null; awayOdds: number | null }>();

    for (const snapshot of latestByBookAndSide.values()) {
      const row = byBook.get(snapshot.bookmaker) ?? {
        bookmaker: snapshot.bookmaker,
        homeOdds: null,
        awayOdds: null,
      };

      const mappedSide = resolveHomeAwaySide(snapshot);

      if (mappedSide === "home") {
        row.homeOdds = snapshot.odds;
      }
      if (mappedSide === "away") {
        row.awayOdds = snapshot.odds;
      }

      byBook.set(snapshot.bookmaker, row);
    }

    return Array.from(byBook.values()).sort((a, b) => a.bookmaker.localeCompare(b.bookmaker));
  }, [gameOdds]);

  const shouldShowLineMovement = useMemo(() => {
    return new Set(gameOdds.map((snapshot) => snapshot.snapshot_time)).size >= 3;
  }, [gameOdds]);

  const lineChartData = useMemo(
    () =>
      gameOdds.map((snapshot) => ({
        time: new Date(snapshot.snapshot_time).toLocaleTimeString(),
        [snapshot.bookmaker]: snapshot.odds,
      })),
    [gameOdds],
  );

  const lineChartBooks = useMemo(
    () => [...new Set(gameOdds.map((snapshot) => snapshot.bookmaker))].slice(0, 5),
    [gameOdds],
  );

  if (moneylineRows.length < 2) {
    return (
      <div className="rounded-xl border border-gray-800 bg-gray-900 p-4 text-sm text-gray-400">
        <h3 className="mb-2 text-base font-semibold text-gray-200">{matchupTitle}</h3>
        Not enough data
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="h-80 rounded-xl border border-gray-800 bg-gray-900 p-3">
        <h3 className="mb-3 text-sm font-semibold text-gray-200">{matchupTitle}</h3>
        <ResponsiveContainer width="100%" height="90%">
          <BarChart data={moneylineRows} layout="vertical" margin={{ top: 8, right: 24, left: 24, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis type="number" stroke="#9ca3af" />
            <YAxis type="category" dataKey="bookmaker" stroke="#9ca3af" width={100} />
            <Tooltip />
            <Legend />
            <Bar dataKey="homeOdds" name="Home" fill="#f59e0b" radius={[0, 4, 4, 0]} />
            <Bar dataKey="awayOdds" name="Away" fill="#64748b" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {shouldShowLineMovement ? (
        <div className="h-72 rounded-xl border border-gray-800 bg-gray-900 p-3">
          <h3 className="mb-3 text-sm font-semibold text-gray-200">Line Movement</h3>
          <ResponsiveContainer width="100%" height="90%">
            <LineChart data={lineChartData}>
              <XAxis dataKey="time" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" />
              <Tooltip />
              {lineChartBooks.map((book, i) => (
                <Line
                  key={book}
                  dataKey={book}
                  stroke={["#34d399", "#60a5fa", "#f59e0b", "#f87171", "#a78bfa"][i]}
                  dot={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : null}
    </div>
  );
}
