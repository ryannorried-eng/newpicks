import type { Pick } from "../../types";
import { SignalBreakdown } from "./SignalBreakdown";

export function PickDetailRow({ pick }: { pick: Pick }) {
  return (
    <div className="rounded-lg bg-gray-950 p-3 text-xs text-gray-300">
      <SignalBreakdown signals={pick.signals} />
      <div className="mt-3 grid gap-2 md:grid-cols-3">
        <div>Books covered: {pick.data_quality.books_covered}</div>
        <div>Freshness: {pick.data_quality.snapshot_freshness_minutes}m</div>
        <div>Fair vs Implied: {(pick.fair_prob * 100).toFixed(1)}% / {(pick.implied_prob * 100).toFixed(1)}%</div>
      </div>
    </div>
  );
}
