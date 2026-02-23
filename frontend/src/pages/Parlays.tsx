import { useMemo, useState } from "react";
import type { Pick } from "../types";
import { EmptyState } from "../components/common/EmptyState";
import { ParlayCard } from "../components/parlays/ParlayCard";
import { RiskTierTabs } from "../components/parlays/RiskTierTabs";
import { useBuildParlay, useParlaysToday } from "../hooks/useParlays";
import { usePicksToday } from "../hooks/usePicks";

interface Conflict {
  keepId: number;
  removeId: number;
}

const CONFLICT_REASONS = [
  "same_game_opposing_sides_same_market",
  "same_game_same_market",
  "opposing_sides_same_market",
  "same_game_conflict",
];

const getPickGameKey = (pick: Pick): string => {
  if (pick.game_id != null) {
    return `id:${pick.game_id}`;
  }
  return `${pick.away_team} @ ${pick.home_team}`.toLowerCase();
};

const findSameGameMarketConflicts = (selectedPicks: Pick[]): Conflict[] => {
  const keepByKey = new Map<string, number>();
  const conflicts: Conflict[] = [];

  for (const pick of selectedPicks) {
    const key = `${getPickGameKey(pick)}::${pick.market}`;
    const keptPickId = keepByKey.get(key);
    if (keptPickId == null) {
      keepByKey.set(key, pick.id);
      continue;
    }
    conflicts.push({ keepId: keptPickId, removeId: pick.id });
  }

  return conflicts;
};

export default function ParlaysPage() {
  const { data: parlays = [] } = useParlaysToday();
  const { data: picks = [] } = usePicksToday();
  const [tier, setTier] = useState<"conservative" | "moderate" | "aggressive">("conservative");
  const [selected, setSelected] = useState<number[]>([]);
  const [warningMessage, setWarningMessage] = useState<string | null>(null);
  const build = useBuildParlay();

  const picksById = useMemo(() => new Map(picks.map((pick) => [pick.id, pick])), [picks]);

  const filtered = useMemo(() => parlays.filter((p) => p.risk_level === tier).slice(0, 3), [parlays, tier]);

  const selectedPicks = useMemo(
    () => selected.map((id) => picksById.get(id)).filter((pick): pick is Pick => pick != null),
    [picksById, selected],
  );

  const removeConflictingAndAnalyze = (pickIds: number[], conflicts: Conflict[]): number[] => {
    const removeIds = new Set(conflicts.map((conflict) => conflict.removeId));
    const cleanedSelection = pickIds.filter((id) => !removeIds.has(id));
    const firstRemoved = conflicts[0] ? picksById.get(conflicts[0].removeId) : null;

    if (firstRemoved) {
      setWarningMessage(`Removed conflicting pick: ${firstRemoved.side} — can't parlay opposing sides of the same game`);
    }

    setSelected(cleanedSelection);
    if (cleanedSelection.length >= 2) {
      build.mutate(cleanedSelection);
    }

    return cleanedSelection;
  };

  const handleAnalyze = () => {
    setWarningMessage(null);

    const conflicts = findSameGameMarketConflicts(selectedPicks);
    if (conflicts.length > 0) {
      removeConflictingAndAnalyze(selected, conflicts);
      return;
    }

    build.mutate(selected, {
      onSuccess: (response) => {
        if (!response.is_valid && CONFLICT_REASONS.some((reason) => response.reason.includes(reason))) {
          const refreshedSelectedPicks = selected
            .map((id) => picksById.get(id))
            .filter((pick): pick is Pick => pick != null);
          const postApiConflicts = findSameGameMarketConflicts(refreshedSelectedPicks);
          if (postApiConflicts.length > 0) {
            removeConflictingAndAnalyze(selected, postApiConflicts);
          }
        }
      },
    });
  };

  return (
    <div className="space-y-6">
      <section>
        <RiskTierTabs active={tier} onChange={setTier} />
        <div className="grid gap-3 md:grid-cols-2">{filtered.length ? filtered.map((parlay) => <ParlayCard key={parlay.id} parlay={parlay} />) : <EmptyState title="No parlays" description={`Not enough qualifying picks for ${tier} parlays`} />}</div>
      </section>
      <section className="rounded-xl border border-gray-800 bg-gray-900 p-4">
        <h3 className="mb-3 text-lg">Interactive Builder</h3>
        {warningMessage && <p className="mb-2 rounded border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-300">{warningMessage}</p>}
        <div className="space-y-2">{picks.map((pick) => <label key={pick.id} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={selected.includes(pick.id)} onChange={(e) => setSelected((prev) => e.target.checked ? [...prev, pick.id] : prev.filter((id) => id !== pick.id))} />{pick.away_team} @ {pick.home_team} — {pick.side}</label>)}</div>
        <button className="mt-3 rounded bg-emerald-600 px-3 py-2 text-sm" onClick={handleAnalyze}>Analyze Parlay</button>
        {build.data && build.data.is_valid && (
          <p className="mt-2 text-sm text-emerald-400">
            Combined EV: {build.data.combined_ev_pct != null ? `+${build.data.combined_ev_pct.toFixed(2)}%` : "N/A"} · Correlation: {build.data.correlation_score != null ? build.data.correlation_score.toFixed(2) : "N/A"}
          </p>
        )}
      </section>
    </div>
  );
}
