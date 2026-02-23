import clsx from "clsx";
import type { Parlay } from "../../types";
import { ParlayLegList } from "./ParlayLegList";

export function ParlayCard({ parlay }: { parlay: Parlay }) {
  return (
    <article className="rounded-xl border border-gray-800 bg-gray-900 p-4">
      <div className="flex items-center justify-between"><span className={clsx("rounded px-2 py-1 text-xs capitalize", parlay.risk_level === "conservative" && "bg-blue-500/20 text-blue-400", parlay.risk_level === "moderate" && "bg-amber-500/20 text-amber-400", parlay.risk_level === "aggressive" && "bg-red-500/20 text-red-400")}>{parlay.risk_level}</span><span className="font-mono text-lg">{parlay.combined_odds_american > 0 ? "+" : ""}{parlay.combined_odds_american}</span></div>
      <div className="mt-2 text-sm text-gray-300">EV {parlay.combined_ev_pct != null ? `+${parlay.combined_ev_pct.toFixed(1)}%` : "N/A"} · {parlay.num_legs} legs</div>
      <div className="text-xs text-gray-500">Kelly {parlay.suggested_kelly_fraction != null ? parlay.suggested_kelly_fraction.toFixed(3) : "N/A"}</div>
      <ParlayLegList legs={parlay.legs} />
    </article>
  );
}
