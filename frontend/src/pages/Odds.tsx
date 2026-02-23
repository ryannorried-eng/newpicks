import { useMemo, useState } from "react";
import { LineMovementChart } from "../components/odds/LineMovementChart";
import { OddsComparisonTable } from "../components/odds/OddsComparisonTable";
import { useLiveOdds } from "../hooks/useOdds";

export default function OddsPage() {
  const { data = [] } = useLiveOdds();
  const games = useMemo(() => {
    const byGameId = new Map<number, { game_id: number; home_team: string; away_team: string }>();
    for (const snapshot of data) {
      if (!byGameId.has(snapshot.game_id)) {
        byGameId.set(snapshot.game_id, {
          game_id: snapshot.game_id,
          home_team: snapshot.home_team,
          away_team: snapshot.away_team,
        });
      }
    }
    return Array.from(byGameId.values());
  }, [data]);
  const [gameId, setGameId] = useState<number | null>(null);

  return (
    <div className="space-y-4">
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
