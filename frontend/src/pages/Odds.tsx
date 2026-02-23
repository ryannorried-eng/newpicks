import { useMemo, useState } from "react";
import { LineMovementChart } from "../components/odds/LineMovementChart";
import { OddsComparisonTable } from "../components/odds/OddsComparisonTable";
import { useLiveOdds } from "../hooks/useOdds";

const SPORT_LABELS: Record<string, string> = {
  basketball_nba: "NBA",
  basketball_ncaab: "NCAAB",
  icehockey_nhl: "NHL",
  americanfootball_ncaaf: "NCAAF",
};

const SPORT_TABS = ["basketball_nba", "basketball_ncaab", "icehockey_nhl", "americanfootball_ncaaf"];

export default function OddsPage() {
  const { data = [] } = useLiveOdds();
  const [sport, setSport] = useState<string>("all");
  const [gameId, setGameId] = useState<number | null>(null);

  const sportSnapshotCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const snapshot of data) {
      counts.set(snapshot.sport_key, (counts.get(snapshot.sport_key) ?? 0) + 1);
    }
    return counts;
  }, [data]);

  const games = useMemo(() => {
    const byGameId = new Map<number, { game_id: number; home_team: string; away_team: string; sport_key: string }>();
    for (const snapshot of data) {
      if (!byGameId.has(snapshot.game_id)) {
        byGameId.set(snapshot.game_id, {
          game_id: snapshot.game_id,
          home_team: snapshot.home_team,
          away_team: snapshot.away_team,
          sport_key: snapshot.sport_key,
        });
      }
    }

    const uniqueGames = Array.from(byGameId.values());
    if (sport === "all") {
      return uniqueGames;
    }

    return uniqueGames.filter((game) => game.sport_key === sport);
  }, [data, sport]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => {
            setSport("all");
            setGameId(null);
          }}
          className={`rounded-lg px-3 py-2 text-sm ${sport === "all" ? "bg-amber-500/20 text-amber-300" : "bg-gray-900 text-gray-400"}`}
        >
          All
        </button>
        {SPORT_TABS.map((sportKey) => (
          <button
            key={sportKey}
            type="button"
            disabled={!sportSnapshotCounts.get(sportKey)}
            onClick={() => {
              setSport(sportKey);
              setGameId(null);
            }}
            className={`rounded-lg px-3 py-2 text-sm transition-colors ${
              !sportSnapshotCounts.get(sportKey)
                ? "cursor-not-allowed bg-gray-900/60 text-gray-600"
                : sport === sportKey
                  ? "bg-amber-500/20 text-amber-300"
                  : "bg-gray-900 text-gray-400 hover:text-gray-200"
            }`}
          >
            {SPORT_LABELS[sportKey] ?? sportKey}
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
      <OddsComparisonTable odds={data} gameId={gameId} />
      <LineMovementChart odds={data} gameId={gameId} />
    </div>
  );
}
