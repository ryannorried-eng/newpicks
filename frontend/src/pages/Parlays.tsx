import { useMemo, useState } from "react";
import { EmptyState } from "../components/common/EmptyState";
import { ParlayCard } from "../components/parlays/ParlayCard";
import { RiskTierTabs } from "../components/parlays/RiskTierTabs";
import { useBuildParlay, useParlaysToday } from "../hooks/useParlays";
import { usePicksToday } from "../hooks/usePicks";

export default function ParlaysPage() {
  const { data: parlays = [] } = useParlaysToday();
  const { data: picks = [] } = usePicksToday();
  const [tier, setTier] = useState<"conservative" | "moderate" | "aggressive">("conservative");
  const [selected, setSelected] = useState<number[]>([]);
  const build = useBuildParlay();

  const filtered = useMemo(() => parlays.filter((p) => p.risk_level === tier).slice(0, 3), [parlays, tier]);

  return (
    <div className="space-y-6">
      <section>
        <RiskTierTabs active={tier} onChange={setTier} />
        <div className="grid gap-3 md:grid-cols-2">{filtered.length ? filtered.map((parlay) => <ParlayCard key={parlay.id} parlay={parlay} />) : <EmptyState title="No parlays" description={`Not enough qualifying picks for ${tier} parlays`} />}</div>
      </section>
      <section className="rounded-xl border border-gray-800 bg-gray-900 p-4">
        <h3 className="mb-3 text-lg">Interactive Builder</h3>
        <div className="space-y-2">{picks.map((pick) => <label key={pick.id} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={selected.includes(pick.id)} onChange={(e) => setSelected((prev) => e.target.checked ? [...prev, pick.id] : prev.filter((id) => id !== pick.id))} />{pick.away_team} @ {pick.home_team} — {pick.side}</label>)}</div>
        <button className="mt-3 rounded bg-emerald-600 px-3 py-2 text-sm" onClick={() => build.mutate(selected)}>Analyze Parlay</button>
        {build.data && <p className="mt-2 text-sm text-emerald-400">Combined EV: +{build.data.combined_ev_pct.toFixed(2)}% · Correlation: {build.data.correlation_score.toFixed(2)}</p>}
      </section>
    </div>
  );
}
