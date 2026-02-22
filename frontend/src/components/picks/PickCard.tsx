import type { Pick } from "../../types";
import { ConfidenceBadge } from "../common/ConfidenceBadge";
import { EVBadge } from "../common/EVBadge";
import { SportIcon } from "../common/SportIcon";

export function PickCard({ pick }: { pick: Pick }) {
  return (
    <article className="rounded-xl border border-gray-800 bg-gray-900 p-4">
      <div className="flex items-center justify-between"><div className="flex items-center gap-2 text-sm text-gray-300"><SportIcon sport={pick.sport_key} /> {pick.sport_key}</div><EVBadge ev={pick.ev_pct} /></div>
      <h3 className="mt-2 text-gray-100">{pick.away_team} @ {pick.home_team}</h3>
      <div className="mt-1 text-sm text-gray-400">{pick.market}: {pick.side} {pick.line ?? ""}</div>
      <div className="mt-2 flex flex-wrap gap-2 text-xs"><span className="font-mono">{pick.odds_american > 0 ? "+" : ""}{pick.odds_american}</span><span className="rounded bg-gray-800 px-2 py-1">{pick.best_book}</span><ConfidenceBadge tier={pick.confidence_tier} /><span className="font-mono text-gray-300">{pick.suggested_kelly_fraction.toFixed(2)}u</span></div>
      <div className="mt-2 text-xs text-gray-500">{new Date(pick.commence_time).toLocaleString()}</div>
    </article>
  );
}
