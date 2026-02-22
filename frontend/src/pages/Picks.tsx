import { useMemo, useState } from "react";
import { EmptyState } from "../components/common/EmptyState";
import { PicksTable } from "../components/picks/PicksTable";
import { usePicksHistory } from "../hooks/usePicks";

export default function PicksPage() {
  const { data = [] } = usePicksHistory();
  const [sport, setSport] = useState("all");
  const [market, setMarket] = useState("all");
  const [confidence, setConfidence] = useState("all");
  const filtered = useMemo(
    () => data.filter((p) => (sport === "all" || p.sport_key.includes(sport)) && (market === "all" || p.market === market) && (confidence === "all" || p.confidence_tier === confidence)),
    [data, sport, market, confidence],
  );

  return (
    <div className="space-y-4">
      <div className="grid gap-2 rounded-xl border border-gray-800 bg-gray-900 p-3 md:grid-cols-4">
        <select className="rounded bg-gray-800 p-2" value={sport} onChange={(e) => setSport(e.target.value)}><option value="all">All Sports</option><option value="nba">NBA</option><option value="nfl">NFL</option><option value="mlb">MLB</option><option value="nhl">NHL</option><option value="ncaab">NCAAB</option></select>
        <select className="rounded bg-gray-800 p-2" value={market} onChange={(e) => setMarket(e.target.value)}><option value="all">All Markets</option><option value="h2h">Moneyline</option><option value="spreads">Spread</option><option value="totals">Total</option></select>
        <select className="rounded bg-gray-800 p-2" value={confidence} onChange={(e) => setConfidence(e.target.value)}><option value="all">All Confidence</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select>
        <select className="rounded bg-gray-800 p-2"><option>Today</option><option>Yesterday</option><option>Last 7 Days</option></select>
      </div>
      {filtered.length ? <PicksTable picks={filtered} /> : <EmptyState title="No picks found" description="Try adjusting filters." />}
    </div>
  );
}
