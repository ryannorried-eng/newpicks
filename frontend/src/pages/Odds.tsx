import { useMemo, useState } from "react";
import { LineMovementChart } from "../components/odds/LineMovementChart";
import { OddsComparisonTable } from "../components/odds/OddsComparisonTable";
import { useLiveOdds } from "../hooks/useOdds";

export default function OddsPage() {
  const { data = [] } = useLiveOdds();
  const gameIds = useMemo(() => [...new Set(data.map((x) => x.game_id))], [data]);
  const [gameId, setGameId] = useState<number | null>(null);

  return (
    <div className="space-y-4">
      <select className="rounded bg-gray-800 p-2" value={gameId ?? ""} onChange={(e) => setGameId(Number(e.target.value) || null)}>
        <option value="">Select game</option>
        {gameIds.map((id) => <option key={id} value={id}>Game {id}</option>)}
      </select>
      <OddsComparisonTable odds={data} gameId={gameId} />
      <LineMovementChart odds={data} gameId={gameId} />
    </div>
  );
}
