import { Fragment, useState } from "react";
import type { Pick } from "../../types";
import { ConfidenceBadge } from "../common/ConfidenceBadge";
import { SportIcon } from "../common/SportIcon";
import { PickDetailRow } from "./PickDetailRow";

export function PicksTable({ picks }: { picks: Pick[] }) {
  const [expandedId, setExpandedId] = useState<number | null>(null);
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-800 bg-gray-900">
      <table className="w-full text-left text-sm">
        <thead className="bg-gray-950 text-gray-400"><tr><th className="p-3">Sport</th><th>Game</th><th>Time</th><th>Market</th><th>Pick</th><th>Odds</th><th>Book</th><th>EV%</th><th>Conf</th><th>Signals</th><th>Kelly</th></tr></thead>
        <tbody>
          {picks.map((pick) => (
            <Fragment key={pick.id}>
              <tr key={pick.id} className="cursor-pointer border-t border-gray-800 hover:bg-gray-800/40" onClick={() => setExpandedId(expandedId === pick.id ? null : pick.id)}>
                <td className="p-3"><div className="flex items-center gap-2"><SportIcon sport={pick.sport_key} />{pick.sport_key}</div></td><td>{pick.away_team} @ {pick.home_team}</td><td>{new Date(pick.commence_time).toLocaleString()}</td><td>{pick.market}</td><td>{pick.side} {pick.line ?? ""}</td><td className="font-mono">{pick.odds_american}</td><td>{pick.best_book}</td><td className="text-emerald-400">{pick.ev_pct.toFixed(1)}%</td><td><ConfidenceBadge tier={pick.confidence_tier} /></td><td>{pick.composite_score.toFixed(2)}</td><td>{pick.suggested_kelly_fraction.toFixed(3)}</td>
              </tr>
              {expandedId === pick.id && <tr className="border-t border-gray-800"><td colSpan={11} className="p-3"><PickDetailRow pick={pick} /></td></tr>}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}
