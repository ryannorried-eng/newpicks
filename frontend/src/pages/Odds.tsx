import { useMemo, useState } from "react";
import { LineMovementChart } from "../components/odds/LineMovementChart";
import { OddsComparisonTable } from "../components/odds/OddsComparisonTable";
import { useLiveOdds } from "../hooks/useOdds";

const SPORT_TABS = ["all", "nba", "ncaab", "nhl", "ncaaf"] as const;
type SportTab = typeof SPORT_TABS[number];

const SPORT_LABELS: Record<SportTab, string> = {
  all: "All",
  nba: "NBA",
  ncaab: "NCAAB",
  nhl: "NHL",
  ncaaf: "NCAAF",
};

function normalizeSportKey(sportKey: string | null | undefined): SportTab | null {
  const value = (sportKey ?? "").toLowerCase();
  if (!value) {
    return null;
  }
  if (value.includes("ncaab")) {
    return "ncaab";
  }
  if (value.includes("nba")) {
    return "nba";
  }
  if (value.includes("ncaaf")) {
    return "ncaaf";
  }
  if (value.includes("nhl")) {
    return "nhl";
  }
  return null;
}

type GameOption = {
  game_id: number;
  home_team: string;
  away_team: string;
  sport: SportTab | null;
};

export default function OddsPage() {
  const { data: rawRows = [] } = useLiveOdds();
  const [sport, setSport] = useState<SportTab>("all");
  const [gameId, setGameId] = useState<number | null>(null);

  const filteredRows = useMemo(() => {
    if (sport === "all") {
      return rawRows;
    }

    return rawRows.filter((snapshot) => normalizeSportKey(snapshot.sport_key) === sport);
  }, [rawRows, sport]);

  const sportSnapshotCounts = useMemo(() => {
    const counts = new Map<SportTab, number>();
    for (const snapshot of rawRows) {
      const normalizedSport = normalizeSportKey(snapshot.sport_key);
      if (!normalizedSport) {
        continue;
      }
      counts.set(normalizedSport, (counts.get(normalizedSport) ?? 0) + 1);
    }
    return counts;
  }, [rawRows]);

  const games = useMemo(() => {
    const byGameKey = new Map<string, GameOption>();
    for (const snapshot of filteredRows) {
      const key = `${snapshot.game_id}|${snapshot.home_team}|${snapshot.away_team}`;
      if (!byGameKey.has(key)) {
        byGameKey.set(key, {
          game_id: snapshot.game_id,
          home_team: snapshot.home_team,
          away_team: snapshot.away_team,
          sport: normalizeSportKey(snapshot.sport_key),
        });
      }
    }
    return Array.from(byGameKey.values());
  }, [filteredRows]);

  console.debug("[OddsPage] rows debug", {
    rawRows: rawRows.length,
    filteredRows: filteredRows.length,
    games: games.length,
    selectedSport: sport,
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {SPORT_TABS.map((sportKey) => (
          <button
            key={sportKey}
            type="button"
            disabled={sportKey !== "all" && !sportSnapshotCounts.get(sportKey)}
            onClick={() => {
              setSport(sportKey);
              setGameId(null);
            }}
            className={`rounded-lg px-3 py-2 text-sm transition-colors ${
              sportKey !== "all" && !sportSnapshotCounts.get(sportKey)
                ? "cursor-not-allowed bg-gray-900/60 text-gray-600"
                : sport === sportKey
                  ? "bg-amber-500/20 text-amber-300"
                  : "bg-gray-900 text-gray-400 hover:text-gray-200"
            }`}
          >
            {SPORT_LABELS[sportKey]}
          </button>
        ))}
      </div>
      <select className="rounded bg-gray-800 p-2" value={gameId ?? ""} onChange={(e) => setGameId(Number(e.target.value) || null)}>
        <option value="">Select game</option>
        {games.map((game) => {
          const awayTeam = game.away_team?.trim();
          const homeTeam = game.home_team?.trim();
          const label = awayTeam && homeTeam ? `${awayTeam} @ ${homeTeam}` : `Game ${game.game_id}`;
          return <option key={game.game_id} value={game.game_id}>{label}</option>;
        })}
      </select>
      <OddsComparisonTable odds={filteredRows} gameId={gameId} />
      <LineMovementChart odds={filteredRows} gameId={gameId} />
    </div>
  );
}
